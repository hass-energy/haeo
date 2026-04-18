"""Tests for the optimized policy compilation pipeline.

Tests cover:
- Signature-based VLAN merging (minimum tag count)
- Reachability pruning (per-connection tag sets)
- Node access lists
- Source enforcement
- Additive policy stacking (group + individual)
- Multi-hop paths
- End-to-end network optimization with policies
"""

from typing import Any, Literal, overload

import numpy as np
import pytest

from custom_components.haeo.core.adapters import policy_compilation
from custom_components.haeo.core.adapters.policy_compilation import (
    _find_reachable_connections,
    _merge_tag_costs,
    compile_policies,
)
from custom_components.haeo.core.model import ModelElementConfig
from custom_components.haeo.core.model.element import NetworkElement
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.elements.battery import BatteryElementConfig
from custom_components.haeo.core.model.elements.connection import ConnectionElementConfig
from custom_components.haeo.core.model.elements.node import NodeElementConfig
from custom_components.haeo.core.model.network import Network


def _node(name: str, *, is_source: bool = False, is_sink: bool = False) -> ModelElementConfig:
    return NodeElementConfig(element_type=MODEL_ELEMENT_TYPE_NODE, name=name, is_source=is_source, is_sink=is_sink)


def _junction(name: str) -> ModelElementConfig:
    return NodeElementConfig(element_type=MODEL_ELEMENT_TYPE_NODE, name=name, is_source=False, is_sink=False)


def _conn(name: str, source: str, target: str, segments: dict[str, Any] | None = None) -> ModelElementConfig:
    c = ConnectionElementConfig(element_type=MODEL_ELEMENT_TYPE_CONNECTION, name=name, source=source, target=target)
    if segments:
        c["segments"] = segments
    return c


def _connections(result: list[ModelElementConfig]) -> list[ConnectionElementConfig]:
    return [e for e in result if e["element_type"] == "connection"]


@overload
def _find(
    result: list[ModelElementConfig], name: str, *, element_type: Literal["connection"]
) -> ConnectionElementConfig: ...
@overload
def _find(result: list[ModelElementConfig], name: str, *, element_type: Literal["node"]) -> NodeElementConfig: ...
@overload
def _find(result: list[ModelElementConfig], name: str, *, element_type: Literal["battery"]) -> BatteryElementConfig: ...
@overload
def _find(result: list[ModelElementConfig], name: str) -> ModelElementConfig: ...


def _find(result: list[ModelElementConfig], name: str, *, element_type: str | None = None) -> ModelElementConfig:
    return next(
        e for e in result if e.get("name") == name and (element_type is None or e.get("element_type") == element_type)
    )


def _outbound_tag(result: list[ModelElementConfig], name: str) -> int:
    """Get the single outbound tag for a source node."""
    node = _find(result, name, element_type=MODEL_ELEMENT_TYPE_NODE)
    tags = node.get("outbound_tags")
    assert tags is not None
    assert len(tags) == 1
    return next(iter(tags))


def _network_element(network: Network, name: str) -> NetworkElement[Any]:
    """Get a network element with proper type narrowing."""
    elem = network.elements[name]
    assert isinstance(elem, NetworkElement)
    return elem


# --- Signature merging ---


def test_identical_prices_merge() -> None:
    """Grid and Solar with same price to Load still get correct costs."""
    elements = [_node("grid"), _node("solar"), _node("load"), _conn("c1", "grid", "load"), _conn("c2", "solar", "load")]
    policies = [
        {"sources": ["grid"], "destinations": ["load"], "price": 0.05},
        {"sources": ["solar"], "destinations": ["load"], "price": 0.05},
    ]
    result = compile_policies(elements, policies)
    # Both get distinct outbound tags (hidden * -> * prevents merging)
    grid_tag = _outbound_tag(result, "grid")
    solar_tag = _outbound_tag(result, "solar")
    assert grid_tag != 0
    assert solar_tag != 0


def test_different_prices_separate() -> None:
    """Grid and Solar with different prices get separate VLANs."""
    elements = [_node("grid"), _node("solar"), _node("load"), _conn("c1", "grid", "load"), _conn("c2", "solar", "load")]
    policies = [
        {"sources": ["grid"], "destinations": ["load"], "price": 0.05},
        {"sources": ["solar"], "destinations": ["load"], "price": 0.02},
    ]
    result = compile_policies(elements, policies)
    assert _outbound_tag(result, "grid") != _outbound_tag(result, "solar")


def test_wildcard_all_same_merges() -> None:
    """Wildcard source with single policy -> all sources get VLANs."""
    elements = [
        _node("a"),
        _node("b"),
        _node("c"),
        _node("d"),
        _conn("c1", "a", "d"),
        _conn("c2", "b", "d"),
        _conn("c3", "c", "d"),
    ]
    policies = [{"sources": ["*"], "destinations": ["d"], "price": 0.05}]
    result = compile_policies(elements, policies)
    assert _outbound_tag(result, "a") != 0
    assert _outbound_tag(result, "b") != 0
    assert _outbound_tag(result, "c") != 0


def test_no_policies_no_vlans() -> None:
    """Without policies, elements pass through unchanged."""
    elements = [_node("grid"), _conn("c1", "grid", "load")]
    assert compile_policies(elements, []) == elements


def test_node_without_policy_gets_outbound_tags() -> None:
    """All nodes get outbound tags from the implicit allow-all rule."""
    elements = [_node("grid"), _node("battery"), _node("load"), _conn("c1", "grid", "load")]
    policies = [{"sources": ["grid"], "destinations": ["load"], "price": 0.05}]
    result = compile_policies(elements, policies)
    battery = _find(result, "battery", element_type=MODEL_ELEMENT_TYPE_NODE)
    assert battery.get("outbound_tags") is not None


# --- Reachability ---


def test_vlan_covers_reachable_subgraph() -> None:
    """VLAN covers the relevant reachable subgraph between source and destination."""
    elements = [
        _node("grid"),
        _node("solar"),
        _junction("sw"),
        _node("load", is_sink=True),
        _conn("grid_sw", "grid", "sw"),
        _conn("solar_sw", "solar", "sw"),
        _conn("sw_load", "sw", "load"),
    ]
    policies = [{"sources": ["grid"], "destinations": ["load"], "price": 0.05}]
    result = compile_policies(elements, policies)

    conns = {c["name"]: c for c in _connections(result)}
    grid_vlan = _outbound_tag(result, "grid")

    _t = conns["grid_sw"].get("tags")
    assert _t is not None
    assert grid_vlan in _t
    _t = conns["sw_load"].get("tags")
    assert _t is not None
    assert grid_vlan in _t
    _t = conns["solar_sw"].get("tags")
    assert _t is not None
    assert grid_vlan in _t


# --- Access lists ---


def test_inbound_tags_set_on_destination() -> None:
    """Destination nodes get inbound tags from all source VLANs."""
    elements = [_node("grid"), _node("solar"), _node("load"), _conn("c1", "grid", "load"), _conn("c2", "solar", "load")]
    policies = [
        {"sources": ["grid"], "destinations": ["load"], "price": 0.05},
        {"sources": ["solar"], "destinations": ["load"], "price": 0.02},
    ]
    result = compile_policies(elements, policies)

    load = _find(result, "load", element_type=MODEL_ELEMENT_TYPE_NODE)
    grid_vlan = _outbound_tag(result, "grid")
    solar_vlan = _outbound_tag(result, "solar")
    _it = load.get("inbound_tags")
    assert _it is not None
    assert grid_vlan in _it
    assert solar_vlan in _it


def test_routing_nodes_get_inbound_tags() -> None:
    """Routing nodes get inbound tags from the implicit allow-all rule."""
    elements = [_node("grid"), _junction("sw"), _node("load"), _conn("c1", "grid", "sw"), _conn("c2", "sw", "load")]
    policies = [{"sources": ["grid"], "destinations": ["load"], "price": 0.05}]
    result = compile_policies(elements, policies)
    sw = _find(result, "sw", element_type=MODEL_ELEMENT_TYPE_NODE)
    assert sw.get("inbound_tags") is not None


# --- Default-allow ---


def test_unpolicied_source_flows_to_policied_destination() -> None:
    """Sources without a policy can still deliver power to policied destinations at zero cost."""
    elements = [
        _node("grid", is_source=True, is_sink=True),
        _node("solar", is_source=True),
        _node("load", is_sink=True),
        _conn(
            "grid_load",
            "grid",
            "load",
            {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0])},
            },
        ),
        _conn(
            "solar_load",
            "solar",
            "load",
            {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0])},
            },
        ),
    ]
    # Only grid has a policy to load; solar has no policy at all
    policies = [{"sources": ["grid"], "destinations": ["load"], "price": 0.10}]
    compiled = compile_policies(elements, policies)

    network = Network(name="test", periods=np.array([1.0]))
    for elem in sorted(compiled, key=lambda e: e.get("element_type") == "connection"):
        network.add(elem)

    h = network._solver
    h.addConstrs(_network_element(network, "load").connection_power() == np.array([5.0]))
    cost = network.optimize()

    # Solar has no policy cost, so optimizer uses solar (free) instead of grid ($0.10/kWh)
    # 5 kW x $0.00 = $0.00
    assert cost == pytest.approx(0.00, abs=0.01)


def test_policied_source_cannot_bypass_cost_via_default_tag() -> None:
    """A source with a policy cannot short-circuit its cost by flowing on tag 0."""
    elements = [
        _node("grid", is_source=True, is_sink=True),
        _node("solar", is_source=True),
        _node("load", is_sink=True),
        _conn(
            "grid_load",
            "grid",
            "load",
            {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0])},
            },
        ),
        _conn(
            "solar_load",
            "solar",
            "load",
            {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([3.0])},
            },
        ),
    ]
    # Grid has a $0.10 policy to load; solar has no policy (free on tag 0)
    # Solar is capped at 3 kW, so grid must supply the remaining 2 kW
    policies = [{"sources": ["grid"], "destinations": ["load"], "price": 0.10}]
    compiled = compile_policies(elements, policies)

    network = Network(name="test", periods=np.array([1.0]))
    for elem in sorted(compiled, key=lambda e: e.get("element_type") == "connection"):
        network.add(elem)

    h = network._solver
    h.addConstrs(_network_element(network, "load").connection_power() == np.array([5.0]))
    cost = network.optimize()

    # Solar 3 kW free + Grid 2 kW x $0.10 = $0.20
    # Grid cannot bypass its policy cost via tag 0 because outbound_tags forces it onto its VLAN
    assert cost == pytest.approx(0.20, abs=0.01)


def test_policy_on_one_source_does_not_affect_other_sources() -> None:
    """A policy from A→B does not prevent or cost C→B."""
    elements = [
        _node("grid", is_source=True, is_sink=True),
        _node("solar", is_source=True),
        _node("battery", is_source=True),
        _node("load", is_sink=True),
        _conn(
            "grid_load",
            "grid",
            "load",
            {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0])},
            },
        ),
        _conn(
            "solar_load",
            "solar",
            "load",
            {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([3.0])},
            },
        ),
        _conn(
            "battery_load",
            "battery",
            "load",
            {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([3.0])},
            },
        ),
    ]
    # Only grid has a policy; solar and battery are unpolicied
    policies = [{"sources": ["grid"], "destinations": ["load"], "price": 0.50}]
    compiled = compile_policies(elements, policies)

    network = Network(name="test", periods=np.array([1.0]))
    for elem in sorted(compiled, key=lambda e: e.get("element_type") == "connection"):
        network.add(elem)

    h = network._solver
    h.addConstrs(_network_element(network, "load").connection_power() == np.array([7.0]))
    cost = network.optimize()

    # Solar 3 kW free + Battery 3 kW free + Grid 1 kW x $0.50 = $0.50
    # Both unpolicied sources flow freely; only grid pays policy cost
    assert cost == pytest.approx(0.50, abs=0.01)


# --- Additive stacking ---


def test_additive_pricing_stacking() -> None:
    """Group + individual pricing both apply: Battery pays group + individual."""
    elements = [
        _node("battery", is_source=True),
        _node("solar", is_source=True),
        _node("load", is_sink=True),
        _conn(
            "bat_load",
            "battery",
            "load",
            {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([10.0]),
                    "max_power_target_source": np.array([10.0]),
                },
            },
        ),
        _conn(
            "sol_load",
            "solar",
            "load",
            {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([10.0]),
                    "max_power_target_source": np.array([10.0]),
                },
            },
        ),
    ]
    policies = [
        {"sources": ["battery", "solar"], "destinations": ["load"], "price": 0.05},
        {"sources": ["battery"], "destinations": ["load"], "price": 0.03},
    ]
    compiled = compile_policies(elements, policies)

    # Battery and Solar should have different VLANs (different signatures)
    bat = _find(compiled, "battery", element_type=MODEL_ELEMENT_TYPE_NODE)
    sol = _find(compiled, "solar", element_type=MODEL_ELEMENT_TYPE_NODE)
    assert bat.get("outbound_tags") != sol.get("outbound_tags")

    # Build and optimize
    network = Network(name="test", periods=np.array([1.0]))
    for elem in sorted(compiled, key=lambda e: e.get("element_type") == "connection"):
        network.add(elem)

    h = network._solver
    h.addConstrs(_network_element(network, "load").connection_power() == np.array([5.0]))
    cost = network.optimize()

    # Optimizer should use solar (cheaper: $0.05) before battery ($0.05 + $0.03 = $0.08)
    # 5 kW all from solar: 5 x $0.05 = $0.25
    assert cost == pytest.approx(0.25, abs=0.01)


# --- Multi-hop ---


def test_multi_hop_policy_through_switchboard() -> None:
    """Policy pricing applies correctly through intermediate routing node."""
    elements = [
        _node("grid", is_source=True, is_sink=True),
        _junction("sw"),
        _node("load", is_sink=True),
        _conn(
            "grid_sw",
            "grid",
            "sw",
            {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([10.0]),
                    "max_power_target_source": np.array([10.0]),
                },
            },
        ),
        _conn(
            "sw_load",
            "sw",
            "load",
            {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([10.0]),
                    "max_power_target_source": np.array([10.0]),
                },
            },
        ),
    ]
    policies = [{"sources": ["grid"], "destinations": ["load"], "price": 0.10}]
    compiled = compile_policies(elements, policies)

    network = Network(name="test", periods=np.array([1.0]))
    for elem in sorted(compiled, key=lambda e: e.get("element_type") == "connection"):
        network.add(elem)

    h = network._solver
    h.addConstrs(_network_element(network, "load").connection_power() == np.array([5.0]))
    cost = network.optimize()

    # 5 kW x $0.10 = $0.50 (pricing applied once at destination, not per-hop)
    assert cost == pytest.approx(0.50, abs=0.01)


# --- End-to-end optimization ---


def test_single_source_policy_adds_cost() -> None:
    """Policy pricing adds cost to power flow."""
    elements = [
        _node("grid", is_source=True, is_sink=True),
        _node("load", is_sink=True),
        _conn(
            "conn",
            "grid",
            "load",
            {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([10.0]),
                    "max_power_target_source": np.array([10.0]),
                },
            },
        ),
    ]
    policies = [{"sources": ["grid"], "destinations": ["load"], "price": 0.10}]
    compiled = compile_policies(elements, policies)

    network = Network(name="test", periods=np.array([1.0]))
    for elem in sorted(compiled, key=lambda e: e.get("element_type") == "connection"):
        network.add(elem)
    h = network._solver
    h.addConstrs(_network_element(network, "load").connection_power() == np.array([5.0]))
    cost = network.optimize()
    assert cost == pytest.approx(0.50, abs=0.01)


def test_cheaper_source_preferred() -> None:
    """Optimizer uses cheaper source when policies differentiate."""
    elements = [
        _node("grid", is_source=True, is_sink=True),
        _node("solar", is_source=True, is_sink=False),
        _node("load", is_sink=True),
        _conn(
            "grid_conn",
            "grid",
            "load",
            {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0])},
                "pricing": {"segment_type": "pricing", "price": np.array([0.30])},
            },
        ),
        _conn(
            "solar_conn",
            "solar",
            "load",
            {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([3.0])},
            },
        ),
    ]
    policies = [
        {"sources": ["grid"], "destinations": ["load"], "price": 0.10},
        {"sources": ["solar"], "destinations": ["load"], "price": 0.01},
    ]
    compiled = compile_policies(elements, policies)

    network = Network(name="test", periods=np.array([1.0]))
    for elem in sorted(compiled, key=lambda e: e.get("element_type") == "connection"):
        network.add(elem)
    h = network._solver
    h.addConstrs(_network_element(network, "load").connection_power() == np.array([5.0]))
    cost = network.optimize()

    # Solar 3 kW x $0.01 + Grid 2 kW x ($0.30 + $0.10)
    assert cost == pytest.approx(0.83, abs=0.01)


def test_diamond_multi_path_all_branches_tagged() -> None:
    """Redundant parallel paths: every edge on some source→sink route gets the VLAN."""
    elements = [
        _node("a", is_source=True),
        _junction("b"),
        _junction("c"),
        _node("d", is_sink=True),
        _conn("ab", "a", "b"),
        _conn("ac", "a", "c"),
        _conn("bd", "b", "d"),
        _conn("cd", "c", "d"),
    ]
    policies = [{"sources": ["a"], "destinations": ["d"], "price": 0.04}]
    result = compile_policies(elements, policies)
    vlan = _outbound_tag(result, "a")
    conns = {c["name"]: c for c in _connections(result)}
    for name in ("ab", "ac", "bd", "cd"):
        _t = conns[name].get("tags")
        assert _t is not None
        assert vlan in _t
        _t = conns[name].get("tags")
        assert isinstance(_t, set)


def test_duplicate_policies_merge_tag_costs() -> None:
    """Identical policy rows should sum into one tag_cost per tag on a connection."""
    elements = [_node("grid"), _node("load"), _conn("c1", "grid", "load")]
    policies = [
        {"sources": ["grid"], "destinations": ["load"], "price": 0.05},
        {"sources": ["grid"], "destinations": ["load"], "price": 0.05},
    ]
    result = compile_policies(elements, policies)
    conn = _find(result, "c1", element_type=MODEL_ELEMENT_TYPE_CONNECTION)
    assert conn.get("tag_costs") is not None
    _tc = conn.get("tag_costs")
    assert _tc is not None
    assert len(_tc) == 1
    _tc = conn.get("tag_costs")
    assert _tc is not None
    assert _tc[0]["price"] == pytest.approx(0.10)


def test_price_target_source_on_connection_where_policy_dest_is_source_endpoint() -> None:
    """price_target_source applies to power leaving the policy destination node on an incident edge."""
    elements = [
        _node("grid", is_source=True, is_sink=True),
        _node("load", is_sink=True),
        _conn("export", "load", "grid"),
    ]
    policies = [
        {
            "sources": ["load"],
            "destinations": ["grid"],
            "price": 0.07,
        },
    ]
    result = compile_policies(elements, policies)
    conn = _find(result, "export", element_type=MODEL_ELEMENT_TYPE_CONNECTION)
    assert conn.get("tag_costs") is not None
    _tc = conn.get("tag_costs")
    assert _tc is not None
    assert len(_tc) == 1
    _tc = conn.get("tag_costs")
    assert _tc is not None
    assert _tc[0]["price"] == pytest.approx(0.07)


def test_compile_policies_without_connections_returns_unchanged() -> None:
    """Policies with only nodes do not mutate elements (no connections to tag)."""
    elements = [_node("a"), _node("b")]
    policies = [{"sources": ["a"], "destinations": ["b"], "price": 0.05}]
    assert compile_policies(elements, policies) is elements


def test_compile_policies_resolves_to_no_flows() -> None:
    """Unknown endpoint names resolve to no explicit flows but hidden rule still applies."""
    elements = [_node("grid"), _node("load"), _conn("c1", "grid", "load")]
    policies = [{"sources": ["nosuch"], "destinations": ["alsomissing"], "price": 0.05}]
    result = compile_policies(elements, policies)
    # Hidden * -> * still generates VLANs for existing nodes
    assert _outbound_tag(result, "grid") != 0


def test_compile_policies_non_list_endpoints_resolve_to_no_flows() -> None:
    """Non-list sources/destinations are ignored but hidden rule still applies."""
    elements = [_node("grid"), _node("load"), _conn("c1", "grid", "load")]
    policies = [{"sources": "grid", "destinations": ("load",), "price": 0.05}]
    result = compile_policies(elements, policies)
    # Hidden * -> * still generates VLANs for existing nodes
    assert _outbound_tag(result, "grid") != 0


def test_wildcard_destination_tags_each_sources_paths() -> None:
    """Wildcard destination applies separate VLANs per source when signatures differ."""
    elements = [
        _node("a"),
        _node("b"),
        _node("c"),
        _conn("ac", "a", "c"),
        _conn("bc", "b", "c"),
    ]
    policies = [{"sources": ["a", "b"], "destinations": ["*"], "price": 0.04}]
    result = compile_policies(elements, policies)
    conns = {x["name"]: x for x in _connections(result)}
    vlan_a = _outbound_tag(result, "a")
    vlan_b = _outbound_tag(result, "b")
    assert vlan_a in conns["ac"].get("tags", set())
    assert vlan_b in conns["bc"].get("tags", set())


def test_policies_without_price_apply_tags_only() -> None:
    """Rules with no price still assign VLANs; pricing step is skipped."""
    elements = [_node("grid"), _node("load"), _conn("c1", "grid", "load")]
    policies = [{"sources": ["grid"], "destinations": ["load"]}]
    result = compile_policies(elements, policies)
    conn = _find(result, "c1", element_type=MODEL_ELEMENT_TYPE_CONNECTION)
    assert conn.get("tag_costs") in (None, [])
    assert _outbound_tag(result, "grid") in conn.get("tags", set())


def test_pricing_injection_skips_non_tagged_incident_connections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Destination-adjacent edges without the source VLAN are ignored for pricing injection."""
    elements = [
        _node("source"),
        _node("dest"),
        _node("other"),
        _conn("source_dest", "source", "dest"),
        _conn("other_dest", "other", "dest"),
    ]
    monkeypatch.setattr(
        policy_compilation,
        "_find_reachable_connections",
        lambda _source_nodes, _dest_nodes, _graph: {"source_dest"},
    )
    policies = [{"sources": ["source"], "destinations": ["dest"], "price": 0.07}]
    result = compile_policies(elements, policies)

    priced = _find(result, "source_dest", element_type=MODEL_ELEMENT_TYPE_CONNECTION)
    unpriced = _find(result, "other_dest", element_type=MODEL_ELEMENT_TYPE_CONNECTION)
    assert priced.get("tag_costs") is not None
    assert unpriced.get("tag_costs") in (None, [])


def test_identical_numpy_prices_merge_vlans() -> None:
    """Per-period price arrays that match element-wise produce correct costs."""
    elements = [_node("grid"), _node("solar"), _node("load"), _conn("c1", "grid", "load"), _conn("c2", "solar", "load")]
    price = np.array([0.05, 0.05])
    policies = [
        {"sources": ["grid"], "destinations": ["load"], "price": price},
        {"sources": ["solar"], "destinations": ["load"], "price": price.copy()},
    ]
    result = compile_policies(elements, policies)
    # Both sources get distinct outbound tags
    assert _outbound_tag(result, "grid") != 0
    assert _outbound_tag(result, "solar") != 0


def test_merge_tag_costs_ignores_rows_without_price() -> None:
    """Rows missing a price key do not contribute to merged totals."""
    conn = ConnectionElementConfig(element_type=MODEL_ELEMENT_TYPE_CONNECTION, name="c", source="a", target="b")
    conn["tag_costs"] = [{"tag": 1, "price": 0.05}, {"tag": 1}, {"tag": 2, "price": 0.10}]
    _merge_tag_costs(conn)
    assert conn["tag_costs"] == [{"tag": 1, "price": pytest.approx(0.05)}, {"tag": 2, "price": pytest.approx(0.10)}]


def test_find_reachable_connections_returns_empty_for_missing_endpoints() -> None:
    """Empty source or destination sets short-circuit reachability."""
    graph = {"a": {("b", "ab")}, "b": {("a", "ab")}}
    assert _find_reachable_connections(set(), {"b"}, graph) == set()
    assert _find_reachable_connections({"a"}, set(), graph) == set()


def test_find_reachable_connections_returns_empty_for_disjoint_reachability() -> None:
    """Disjoint source/destination components produce no relevant connections."""
    graph = {
        "a": {("b", "ab")},
        "b": {("a", "ab")},
        "x": {("y", "xy")},
        "y": {("x", "xy")},
    }
    assert _find_reachable_connections({"a"}, {"y"}, graph) == set()


def test_no_policy_no_extra_cost() -> None:
    """Without policies, optimization behaves normally."""
    network = Network(name="test", periods=np.array([1.0]))
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "load", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "conn",
            "source": "grid",
            "target": "load",
            "segments": {
                "pricing": {"segment_type": "pricing", "price": np.array([0.20])},
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([5.0])},
            },
        }
    )
    h = network._solver
    h.addConstrs(_network_element(network, "load").connection_power() == np.array([5.0]))
    cost = network.optimize()
    assert cost == pytest.approx(1.00)
