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
    CompilationResult,
    CompiledPolicyRule,
    _find_reachable_connections,
    _min_cut_edges,
    compile_policies,
)
from custom_components.haeo.core.model import ModelElementConfig
from custom_components.haeo.core.model.element import NetworkElement
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.elements.battery import BatteryElementConfig
from custom_components.haeo.core.model.elements.connection import ConnectionElementConfig
from custom_components.haeo.core.model.elements.node import NodeElementConfig
from custom_components.haeo.core.model.elements.policy_pricing import PolicyPricingElementConfig
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


def _policy(
    sources: list[str],
    destinations: list[str],
    price: float | np.ndarray[Any, np.dtype[np.floating[Any]]] = 0.0,
    *,
    enabled: bool = True,
) -> CompiledPolicyRule:
    rule = CompiledPolicyRule(sources=sources, destinations=destinations, price=price)
    if not enabled:
        rule["enabled"] = False
    return rule


def _connections(result: CompilationResult) -> list[ConnectionElementConfig]:
    return [e for e in result["elements"] if e["element_type"] == "connection"]


def _pricing_configs(result: CompilationResult) -> list[PolicyPricingElementConfig]:
    return [e for e in result["elements"] if e["element_type"] == "policy_pricing"]


@overload
def _find(result: CompilationResult, name: str, *, element_type: Literal["connection"]) -> ConnectionElementConfig: ...
@overload
def _find(result: CompilationResult, name: str, *, element_type: Literal["node"]) -> NodeElementConfig: ...
@overload
def _find(result: CompilationResult, name: str, *, element_type: Literal["battery"]) -> BatteryElementConfig: ...
@overload
def _find(result: CompilationResult, name: str) -> ModelElementConfig: ...


def _find(result: CompilationResult, name: str, *, element_type: str | None = None) -> ModelElementConfig:
    return next(
        e
        for e in result["elements"]
        if e.get("name") == name and (element_type is None or e.get("element_type") == element_type)
    )


def _outbound_tag(result: CompilationResult, name: str) -> int:
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


_ELEMENT_SORT_ORDER = {"node": 0, "battery": 0, "connection": 1, "policy_pricing": 2}


def _build_network(result: CompilationResult) -> Network:
    """Build a network from a CompilationResult, adding elements in correct order."""
    network = Network(name="test", periods=np.array([1.0]))
    for elem in sorted(result["elements"], key=lambda e: _ELEMENT_SORT_ORDER.get(e["element_type"], 1)):
        network.add(elem)
    return network


# --- Signature merging ---


def test_identical_prices_separate_rules_get_separate_vlans() -> None:
    """Sources from separate rules get separate VLANs even with identical prices."""
    elements = [_node("grid"), _node("solar"), _node("load"), _conn("c1", "grid", "load"), _conn("c2", "solar", "load")]
    policies = [
        _policy(["grid"], ["load"], 0.05),
        _policy(["solar"], ["load"], 0.05),
    ]
    result = compile_policies(elements, policies)
    grid_tag = _outbound_tag(result, "grid")
    solar_tag = _outbound_tag(result, "solar")
    assert grid_tag != 0
    assert solar_tag != 0
    assert grid_tag != solar_tag


def test_same_rule_sources_share_vlan() -> None:
    """Sources listed in a single rule share a VLAN regardless of price."""
    elements = [_node("grid"), _node("solar"), _node("load"), _conn("c1", "grid", "load"), _conn("c2", "solar", "load")]
    policies = [
        _policy(["grid", "solar"], ["load"], 0.05),
    ]
    result = compile_policies(elements, policies)
    assert _outbound_tag(result, "grid") == _outbound_tag(result, "solar")


def test_identical_groupings_different_prices_share_vlan() -> None:
    """Rules with the same source/destination grouping share a VLAN even with different prices."""
    elements = [_node("grid"), _node("solar"), _node("load"), _conn("c1", "grid", "load"), _conn("c2", "solar", "load")]
    policies = [
        _policy(["grid", "solar"], ["load"], 0.05),
        _policy(["grid", "solar"], ["load"], 0.03),
    ]
    result = compile_policies(elements, policies)
    assert _outbound_tag(result, "grid") == _outbound_tag(result, "solar")
    assert _outbound_tag(result, "grid") != 0


def test_wildcard_all_same_merges() -> None:
    """Wildcard source with single policy -> all sources get VLANs."""
    elements = [
        _node("a", is_source=True),
        _node("b", is_source=True),
        _node("c", is_source=True),
        _node("d", is_sink=True),
        _conn("c1", "a", "d"),
        _conn("c2", "b", "d"),
        _conn("c3", "c", "d"),
    ]
    policies = [_policy(["*"], ["d"], 0.05)]
    result = compile_policies(elements, policies)
    assert _outbound_tag(result, "a") != 0
    assert _outbound_tag(result, "b") != 0
    assert _outbound_tag(result, "c") != 0


def test_disabled_rule_still_creates_vlans() -> None:
    """Disabled rules compile into VLANs so re-enabling updates reactively."""
    elements = [_node("grid", is_source=True), _node("load", is_sink=True), _conn("c1", "grid", "load")]
    policies = [_policy(["grid"], ["load"], 0.05, enabled=False)]
    result = compile_policies(elements, policies)
    assert _outbound_tag(result, "grid") != 0
    assert len(_pricing_configs(result)) == 1


def test_disabled_rule_has_zero_price() -> None:
    """Disabled rules get zero price in their PolicyPricing elements."""
    elements = [
        _node("grid", is_source=True),
        _node("load", is_sink=True),
        _conn(
            "c1",
            "grid",
            "load",
            {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([10.0]),
                    "max_power_target_source": np.array([10.0]),
                }
            },
        ),
    ]
    policies = [_policy(["grid"], ["load"], 0.50, enabled=False)]
    compiled = compile_policies(elements, policies)
    pricing = _pricing_configs(compiled)
    assert len(pricing) == 1
    assert pricing[0]["price"] == 0.0

    # Optimize: with zero price, cost should be zero
    network = _build_network(compiled)
    h = network._solver
    h.addConstrs(_network_element(network, "load").connection_power() == np.array([5.0]))
    cost = network.optimize()
    assert cost == pytest.approx(0.0, abs=0.01)


def test_disabled_and_enabled_rules_coexist() -> None:
    """Disabled and enabled rules produce correct pricing side by side."""
    elements = [
        _node("grid", is_source=True),
        _node("solar", is_source=True),
        _node("load", is_sink=True),
        _conn(
            "c1",
            "grid",
            "load",
            {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([10.0]),
                    "max_power_target_source": np.array([10.0]),
                }
            },
        ),
        _conn(
            "c2",
            "solar",
            "load",
            {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([10.0]),
                    "max_power_target_source": np.array([10.0]),
                }
            },
        ),
    ]
    policies = [
        _policy(["grid"], ["load"], 0.10, enabled=False),
        _policy(["solar"], ["load"], 0.05),
    ]
    compiled = compile_policies(elements, policies)
    pricing = _pricing_configs(compiled)
    assert len(pricing) == 2
    # One has zero price (disabled), one has 0.05 (enabled)
    prices = sorted(float(p["price"]) for p in pricing)
    assert prices[0] == 0.0
    assert prices[1] == 0.05


def test_no_policies_no_vlans() -> None:
    """Without policies, elements pass through unchanged."""
    elements = [_node("grid"), _conn("c1", "grid", "load")]
    result = compile_policies(elements, [])
    assert result["elements"] is elements
    assert result["pricing_rule_map"] == {}


def test_node_without_policy_gets_outbound_tags() -> None:
    """All source-capable nodes get outbound tags from the implicit allow-all rule."""
    elements = [
        _node("grid", is_source=True),
        _node("battery", is_source=True),
        _node("load", is_sink=True),
        _conn("c1", "grid", "load"),
    ]
    policies = [_policy(["grid"], ["load"], 0.05)]
    result = compile_policies(elements, policies)
    battery = _find(result, "battery", element_type=MODEL_ELEMENT_TYPE_NODE)
    assert battery.get("outbound_tags") is not None


def test_wildcard_excludes_sink_only_from_sources() -> None:
    """Wildcard source expansion excludes nodes that can only consume."""
    elements = [
        _node("solar", is_source=True),
        _node("load", is_sink=True),
        _junction("sw"),
        _conn("solar_sw", "solar", "sw"),
        _conn("sw_load", "sw", "load"),
    ]
    policies = [_policy(["*"], ["load"], 0.05)]
    result = compile_policies(elements, policies)
    # Solar is a source — gets a VLAN
    assert _outbound_tag(result, "solar") != 0
    # Load is sink-only — not expanded as source, no outbound tag
    load = _find(result, "load", element_type=MODEL_ELEMENT_TYPE_NODE)
    assert load.get("outbound_tags") is None
    # Junction is neither — not expanded as source, no outbound tag
    sw = _find(result, "sw", element_type=MODEL_ELEMENT_TYPE_NODE)
    assert sw.get("outbound_tags") is None


def test_wildcard_excludes_source_only_from_destinations() -> None:
    """Wildcard destination expansion excludes nodes that can only produce."""
    elements = [
        _node("grid", is_source=True, is_sink=True),
        _node("solar", is_source=True),
        _node("load", is_sink=True),
        _conn("grid_load", "grid", "load"),
        _conn("grid_solar", "grid", "solar"),
    ]
    policies = [_policy(["grid"], ["*"], 0.05)]
    result = compile_policies(elements, policies)
    # Load (sink) gets inbound tag from grid
    load = _find(result, "load", element_type=MODEL_ELEMENT_TYPE_NODE)
    assert load.get("inbound_tags") is not None
    # Solar (source-only) is not a wildcard destination — no inbound tag from grid policy
    solar = _find(result, "solar", element_type=MODEL_ELEMENT_TYPE_NODE)
    solar_inbound = solar.get("inbound_tags")
    grid_vlan = _outbound_tag(result, "grid")
    # Grid's policy VLAN should not appear in solar's inbound tags
    assert solar_inbound is None or grid_vlan not in solar_inbound


# --- Reachability ---


def test_vlan_covers_reachable_subgraph() -> None:
    """VLAN covers the directed path from source to destination."""
    elements = [
        _node("grid"),
        _node("solar"),
        _junction("sw"),
        _node("load", is_sink=True),
        _conn("grid_sw", "grid", "sw"),
        _conn("solar_sw", "solar", "sw"),
        _conn("sw_load", "sw", "load"),
    ]
    policies = [_policy(["grid"], ["load"], 0.05)]
    result = compile_policies(elements, policies)

    conns = {c["name"]: c for c in _connections(result)}
    grid_vlan = _outbound_tag(result, "grid")

    _t = conns["grid_sw"].get("tags")
    assert _t is not None
    assert grid_vlan in _t
    _t = conns["sw_load"].get("tags")
    assert _t is not None
    assert grid_vlan in _t
    # solar_sw is not on the directed path from grid to load
    _t = conns["solar_sw"].get("tags")
    assert _t is not None
    assert grid_vlan not in _t


# --- Access lists ---


def test_inbound_tags_set_on_destination() -> None:
    """Sink destination nodes get inbound tags including all active VLANs."""
    elements = [
        _node("grid"),
        _node("solar"),
        _node("load", is_sink=True),
        _conn("c1", "grid", "load"),
        _conn("c2", "solar", "load"),
    ]
    policies = [
        _policy(["grid"], ["load"], 0.05),
        _policy(["solar"], ["load"], 0.02),
    ]
    result = compile_policies(elements, policies)

    load = _find(result, "load", element_type=MODEL_ELEMENT_TYPE_NODE)
    grid_vlan = _outbound_tag(result, "grid")
    solar_vlan = _outbound_tag(result, "solar")
    _it = load.get("inbound_tags")
    assert _it is not None
    assert grid_vlan in _it
    assert solar_vlan in _it
    assert 0 in _it  # default tag for unpolicied sources


def test_routing_nodes_get_inbound_tags() -> None:
    """Junctions (non-sinks) don't get inbound tags — they pass power through without consuming."""
    elements = [
        _node("grid", is_source=True),
        _junction("sw"),
        _node("load", is_sink=True),
        _conn("c1", "grid", "sw"),
        _conn("c2", "sw", "load"),
    ]
    policies = [_policy(["grid"], ["load"], 0.05)]
    result = compile_policies(elements, policies)
    sw = _find(result, "sw", element_type=MODEL_ELEMENT_TYPE_NODE)
    # Junction doesn't consume, so no inbound_tags needed
    assert sw.get("inbound_tags") is None
    # But load (the actual sink) does get inbound tags
    load = _find(result, "load", element_type=MODEL_ELEMENT_TYPE_NODE)
    assert load.get("inbound_tags") is not None


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
    policies = [_policy(["grid"], ["load"], 0.10)]
    compiled = compile_policies(elements, policies)

    network = _build_network(compiled)
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
    policies = [_policy(["grid"], ["load"], 0.10)]
    compiled = compile_policies(elements, policies)

    network = _build_network(compiled)
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
    policies = [_policy(["grid"], ["load"], 0.50)]
    compiled = compile_policies(elements, policies)

    network = _build_network(compiled)
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
        _policy(["battery", "solar"], ["load"], 0.05),
        _policy(["battery"], ["load"], 0.03),
    ]
    compiled = compile_policies(elements, policies)

    # Battery participates in two groupings, solar in one — different VLANs.
    bat = _find(compiled, "battery", element_type=MODEL_ELEMENT_TYPE_NODE)
    sol = _find(compiled, "solar", element_type=MODEL_ELEMENT_TYPE_NODE)
    assert bat.get("outbound_tags") != sol.get("outbound_tags")

    # Build and optimize
    network = _build_network(compiled)
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
    policies = [_policy(["grid"], ["load"], 0.10)]
    compiled = compile_policies(elements, policies)

    network = _build_network(compiled)
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
    policies = [_policy(["grid"], ["load"], 0.10)]
    compiled = compile_policies(elements, policies)

    network = _build_network(compiled)
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
        _policy(["grid"], ["load"], 0.10),
        _policy(["solar"], ["load"], 0.01),
    ]
    compiled = compile_policies(elements, policies)

    network = _build_network(compiled)
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
    policies = [_policy(["a"], ["d"], 0.04)]
    result = compile_policies(elements, policies)
    vlan = _outbound_tag(result, "a")
    conns = {c["name"]: c for c in _connections(result)}
    for name in ("ab", "ac", "bd", "cd"):
        _t = conns[name].get("tags")
        assert _t is not None
        assert vlan in _t
        _t = conns[name].get("tags")
        assert isinstance(_t, set)


def test_duplicate_policies_create_separate_pricing_elements() -> None:
    """Identical policy rows create separate pricing elements whose costs stack."""
    elements = [
        _node("grid", is_source=True),
        _node("load", is_sink=True),
        _conn("c1", "grid", "load"),
    ]
    policies = [
        _policy(["grid"], ["load"], 0.05),
        _policy(["grid"], ["load"], 0.05),
    ]
    result = compile_policies(elements, policies)
    pricing = _pricing_configs(result)
    # Each rule creates its own pricing element
    assert len(pricing) == 2
    for p in pricing:
        assert p["price"] == pytest.approx(0.05)


def test_price_target_source_on_connection_creates_pricing_element() -> None:
    """Pricing element is created for power flow from source to destination."""
    elements = [
        _node("grid", is_source=True, is_sink=True),
        _node("load", is_sink=True),
        _conn("export", "load", "grid"),
    ]
    policies = [
        _policy(["load"], ["grid"], 0.07),
    ]
    result = compile_policies(elements, policies)
    pricing = _pricing_configs(result)
    assert len(pricing) == 1
    assert pricing[0]["price"] == pytest.approx(0.07)


def test_compile_policies_without_connections_returns_unchanged() -> None:
    """Policies with only nodes do not mutate elements (no connections to tag)."""
    elements = [_node("a"), _node("b")]
    policies = [_policy(["a"], ["b"], 0.05)]
    result = compile_policies(elements, policies)
    assert result["elements"] is elements
    assert result["pricing_rule_map"] == {}


def test_compile_policies_junctions_only_returns_unchanged() -> None:
    """Wildcards that resolve to no source/sink nodes produce no flows."""
    elements = [_junction("sw1"), _junction("sw2"), _conn("c1", "sw1", "sw2")]
    policies = [_policy(["*"], ["*"], 0.05)]
    result = compile_policies(elements, policies)
    # No source or sink nodes, so wildcard expansion yields no flows — elements unchanged
    assert result["elements"] is elements
    assert result["pricing_rule_map"] == {}


def test_compile_policies_resolves_to_no_flows() -> None:
    """Unknown endpoint names resolve to no flows and no VLANs."""
    elements = [
        _node("grid", is_source=True),
        _node("load", is_sink=True),
        _conn("c1", "grid", "load"),
    ]
    policies = [_policy(["nosuch"], ["alsomissing"], 0.05)]
    result = compile_policies(elements, policies)
    # No valid flows from unknown endpoints — elements pass through unchanged
    assert result["elements"] is elements
    assert result["pricing_rule_map"] == {}


def test_compile_policies_non_list_endpoints_resolve_to_no_flows() -> None:
    """Non-list sources/destinations are ignored and produce no VLANs."""
    elements = [
        _node("grid", is_source=True),
        _node("load", is_sink=True),
        _conn("c1", "grid", "load"),
    ]
    policies: list[CompiledPolicyRule] = [
        {"sources": "grid", "destinations": ("load",), "price": 0.05},  # type: ignore[typeddict-item]
    ]
    result = compile_policies(elements, policies)
    # Non-list endpoints are not resolved — no flows, elements unchanged
    assert result["elements"] is elements
    assert result["pricing_rule_map"] == {}


def test_wildcard_destination_tags_each_sources_paths() -> None:
    """Wildcard destination with same destinations shares VLANs; pricing is per-element."""
    elements = [
        _node("a", is_source=True),
        _node("b", is_source=True),
        _node("c", is_sink=True),
        _conn("ac", "a", "c"),
        _conn("bc", "b", "c"),
    ]
    policies = [_policy(["a", "b"], ["*"], 0.04)]
    result = compile_policies(elements, policies)
    conns = {x["name"]: x for x in _connections(result)}
    vlan_a = _outbound_tag(result, "a")
    vlan_b = _outbound_tag(result, "b")
    assert vlan_a in conns["ac"].get("tags", set())
    assert vlan_b in conns["bc"].get("tags", set())


def test_vlan_reaches_non_policy_sinks() -> None:
    """VLAN membership must cover paths to all sinks, not just policy destinations.

    Regression test: a Solar→Grid policy must still let Solar-tagged flow reach
    Load (a non-policy sink). Restricting VLAN 2 to only Solar→Grid paths would
    force solar surplus to detour through storage, producing spurious
    simultaneous charge/discharge ("washing") in the LP solution.
    """
    elements = [
        _node("solar", is_source=True),
        _node("grid", is_source=True, is_sink=True),
        _node("load", is_sink=True),
        _node("sw"),
        _conn("solar_sw", "solar", "sw"),
        _conn("sw_grid", "sw", "grid"),
        _conn("sw_load", "sw", "load"),
    ]
    policies = [_policy(["solar"], ["grid"], 0.02)]
    result = compile_policies(elements, policies)
    conns = {x["name"]: x for x in _connections(result)}
    vlan_solar = _outbound_tag(result, "solar")

    # Solar's VLAN must be present on every connection from Solar to any sink,
    # including Switchboard→Load (a non-policy sink), so Solar-tagged flow has
    # a direct path to Load without laundering through storage.
    assert vlan_solar in conns["solar_sw"].get("tags", set())
    assert vlan_solar in conns["sw_load"].get("tags", set()), (
        "Solar VLAN must reach non-policy sinks (Load), otherwise solar flow is "
        "forced to detour through battery/storage, producing washing artefacts."
    )
    assert vlan_solar in conns["sw_grid"].get("tags", set())

    # Pricing element should reference only the cut edge(s) separating Solar
    # from Grid (the policy destination); non-policy sinks remain cost-free.
    pricing = _pricing_configs(result)
    assert len(pricing) == 1
    assert pricing[0]["price"] == pytest.approx(0.02)
    # The pricing terms should reference the min-cut connection(s) with the solar VLAN tag
    for term in pricing[0]["terms"]:
        assert term["tag"] == vlan_solar


def test_zero_price_policy_applies_tags_with_zero_cost() -> None:
    """Rules with zero price assign VLANs and create pricing elements with zero cost."""
    elements = [
        _node("grid", is_source=True),
        _node("load", is_sink=True),
        _conn("c1", "grid", "load"),
    ]
    policies = [_policy(["grid"], ["load"], price=0.0)]
    result = compile_policies(elements, policies)
    conn = _find(result, "c1", element_type=MODEL_ELEMENT_TYPE_CONNECTION)
    assert _outbound_tag(result, "grid") in conn.get("tags", set())
    # Zero-price rules still create pricing elements (price=0 means no cost influence)
    pricing = _pricing_configs(result)
    assert len(pricing) > 0
    assert all(p["price"] == 0.0 for p in pricing)


def test_pricing_injection_skips_non_tagged_incident_connections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pricing element terms only reference connections on the min-cut, not untagged ones."""
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
        lambda _source_nodes, _dest_nodes, _graph, **_kwargs: {"source_dest"},
    )
    policies = [_policy(["source"], ["dest"], 0.07)]
    result = compile_policies(elements, policies)

    pricing = _pricing_configs(result)
    assert len(pricing) == 1
    assert pricing[0]["price"] == pytest.approx(0.07)
    # Pricing terms should only reference tagged connections, not untagged ones
    term_connections = {term["connection"] for term in pricing[0]["terms"]}
    assert "source_dest" in term_connections
    assert "other_dest" not in term_connections


def test_identical_numpy_prices_separate_rules_get_separate_vlans() -> None:
    """Sources from separate rules get separate VLANs; each rule creates a pricing element."""
    elements = [
        _node("grid", is_source=True),
        _node("solar", is_source=True),
        _node("load", is_sink=True),
        _conn("c1", "grid", "load"),
        _conn("c2", "solar", "load"),
    ]
    price = np.array([0.05, 0.05])
    policies = [
        _policy(["grid"], ["load"], price),
        _policy(["solar"], ["load"], price.copy()),
    ]
    result = compile_policies(elements, policies)
    # Separate rules → separate VLANs
    grid_tag = _outbound_tag(result, "grid")
    solar_tag = _outbound_tag(result, "solar")
    assert grid_tag != solar_tag
    assert grid_tag != 0
    # Each rule creates its own pricing element
    assert len(_pricing_configs(result)) == 2


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


def test_find_reachable_connections_absorbs_tags_at_sinks() -> None:
    """Tags stop propagating at sink nodes (storage-style absorbing semantics).

    With ``absorb_at`` supplied, forward reachability treats those nodes as
    dead-ends: flow may arrive but does not continue out. This prevents a
    battery (which is both a source and a sink) from laundering an incoming
    VLAN onto its outbound edge, where the tag would bypass costs that were
    placed on the battery's own VLAN.
    """
    # solar → inv → battery → inv → load : without absorption the VLAN
    # from solar would propagate onto battery's outbound edge as well.
    graph = {
        "solar": {("inv", "solar_inv")},
        "inv": {("battery", "battery_charge"), ("load", "inv_load")},
        "battery": {("inv", "battery_discharge")},
    }
    sinks = {"battery", "load"}
    connections = _find_reachable_connections({"solar"}, sinks, graph, absorb_at=sinks)
    assert "battery_discharge" not in connections
    # Still reaches load directly and the battery charge edge
    assert "solar_inv" in connections
    assert "inv_load" in connections
    assert "battery_charge" in connections


def test_find_reachable_connections_does_not_absorb_at_origin() -> None:
    """Origin sources always expand even if they are in the absorbing set.

    A battery's own VLAN must propagate forward from the battery (it is both
    a source and a sink). Including the origin in ``absorb_at`` would
    otherwise stop expansion before it started.
    """
    graph = {
        "battery": {("inv", "battery_discharge")},
        "inv": {("load", "inv_load")},
    }
    sinks = {"battery", "load"}
    connections = _find_reachable_connections({"battery"}, sinks, graph, absorb_at=sinks)
    assert connections == {"battery_discharge", "inv_load"}


def test_find_reachable_connections_excludes_edges_into_source() -> None:
    """Tagged flow cannot re-enter its own source node.

    A battery is both a source and a sink for its own VLAN.  Without this
    exclusion the reachable edge set includes ``Battery:charge`` for the
    battery VLAN, creating a zero-cost self-loop (discharge → inverter →
    charge → battery) that bypasses every downstream cut where the wear
    cost lives.  Excluding edges whose target is the VLAN's own source
    breaks the loop without affecting legitimate source→sink flow.
    """
    # battery → inv → battery forms a self-loop via the charge edge
    graph = {
        "battery": {("inv", "battery_discharge")},
        "inv": {("battery", "battery_charge"), ("load", "inv_load")},
    }
    sinks = {"battery", "load"}
    connections = _find_reachable_connections({"battery"}, sinks, graph, absorb_at=sinks)
    assert "battery_charge" not in connections, (
        "Battery VLAN must not re-enter the battery via its charge edge; "
        "otherwise solver exploits a zero-cost self-loop."
    )
    assert "battery_discharge" in connections
    assert "inv_load" in connections


def test_compile_policies_excludes_battery_self_loop_vlan() -> None:
    """Integration: the battery's own VLAN does not tag its charge edge.

    Closes the zero-wear phantom cycle (Battery:discharge → Inverter →
    Battery:charge → Battery) that would otherwise let solar charge
    incentives fund efficiency-loss losses while sidestepping wear.
    """
    elements = [
        _node("solar", is_source=True),
        _node("battery", is_source=True, is_sink=True),
        _node("load", is_sink=True),
        _junction("inv"),
        _conn("solar_inv", "solar", "inv"),
        _conn("battery_charge", "inv", "battery"),
        _conn("battery_discharge", "battery", "inv"),
        _conn("inv_load", "inv", "load"),
    ]
    policies = [
        _policy(["solar"], ["battery"], -0.001),
        _policy(["battery"], ["*"], 0.01),
    ]
    result = compile_policies(elements, policies)
    conns = {c["name"]: c for c in _connections(result)}
    battery_tag = next(iter((conns["battery_discharge"].get("tags") or set()) - {0}))
    charge_tags = conns["battery_charge"].get("tags") or set()
    assert battery_tag not in charge_tags, "Battery's own VLAN must not tag its own charge edge."


def test_compile_policies_absorbs_solar_tag_at_battery_sink() -> None:
    """Integration: Solar-tagged flow cannot re-emerge from a battery.

    This closes a phantom-arbitrage loop where Solar→Battery:charge with a
    negative charge-incentive could round-trip through Battery:discharge
    while paying no cost, because the battery's wear cut priced only its
    own VLAN.
    """
    elements = [
        _node("solar", is_source=True),
        _node("battery", is_source=True, is_sink=True),
        _node("load", is_sink=True),
        _junction("inv"),
        _conn("solar_inv", "solar", "inv"),
        _conn("battery_charge", "inv", "battery"),
        _conn("battery_discharge", "battery", "inv"),
        _conn("inv_load", "inv", "load"),
    ]
    policies = [
        _policy(["solar"], ["battery"], -0.001),
        _policy(["battery"], ["*"], 0.01),
    ]
    result = compile_policies(elements, policies)
    conns = {c["name"]: c for c in _connections(result)}
    solar_tag = next(iter((conns["solar_inv"].get("tags") or set()) - {0}))
    discharge_tags = conns["battery_discharge"].get("tags") or set()
    assert solar_tag not in discharge_tags, "Solar VLAN must not reach battery discharge"


# --- Min-cut placement ---


def test_min_cut_specific_target_lands_on_target_inbound() -> None:
    """Single source, single target: cut is the target's inbound edge (the discriminator)."""
    # grid → sw → load ; cut separating {grid} from {load} sits on sw_load
    edges = [("grid", "sw", "grid_sw"), ("sw", "load", "sw_load")]
    assert _min_cut_edges({"grid"}, {"load"}, edges) == {"sw_load"}


def test_min_cut_wildcard_target_lands_on_source_outbound() -> None:
    """Source with a single outbound edge: cut is that edge regardless of how many sinks."""
    edges = [
        ("battery", "inv", "bat_inv"),
        ("inv", "sw", "inv_sw"),
        ("sw", "load", "sw_load"),
        ("sw", "grid", "sw_grid"),
    ]
    assert _min_cut_edges({"battery"}, {"load", "grid", "inv"}, edges) == {"bat_inv"}


def test_min_cut_finds_shared_bottleneck_between_multi_source_multi_target() -> None:
    """battery|solar → load|grid with inverter in the middle: the inverter edge is the min cut.

    This is the user's motivating example: the sink-side cut collapses to a
    single bottleneck edge (inverter→switchboard) rather than two target-
    inbound edges, minimising the number of places where constraints /
    costs are installed.
    """
    edges = [
        ("battery", "inv", "bat_inv"),
        ("solar", "inv", "sol_inv"),
        ("inv", "sw", "inv_sw"),
        ("sw", "load", "sw_load"),
        ("sw", "grid", "sw_grid"),
    ]
    assert _min_cut_edges({"battery", "solar"}, {"load", "grid"}, edges) == {"inv_sw"}


def test_min_cut_is_antichain_every_path_crosses_exactly_once() -> None:
    """Antichain property: no two cut edges lie on a single s→t path.

    Diamond topology a→{b,c}→d has two edge-disjoint s-t paths so min-cut
    size is 2; both valid cuts (source-outbound or target-inbound) are
    antichains, but we want the sink-side canonical which is target-inbound.
    """
    edges = [
        ("a", "b", "ab"),
        ("a", "c", "ac"),
        ("b", "d", "bd"),
        ("c", "d", "cd"),
    ]
    # Sink-side canonical cut is target-inbound: {bd, cd}
    cut = _min_cut_edges({"a"}, {"d"}, edges)
    assert cut == {"bd", "cd"}
    # Each s-t path contains exactly one cut edge
    paths = [["ab", "bd"], ["ac", "cd"]]
    for path in paths:
        assert len(set(path) & cut) == 1


def test_min_cut_empty_when_source_or_dest_empty() -> None:
    """Empty source or destination set yields no cut edges."""
    assert _min_cut_edges(set(), {"a"}, [("a", "b", "x")]) == set()
    assert _min_cut_edges({"a"}, set(), [("a", "b", "x")]) == set()


def test_min_cut_ignores_self_loops_in_destinations() -> None:
    """Self-loops (source ∈ destinations) do not collapse the cut to empty.

    A source that also appears in the destination set (e.g. from wildcard
    expansion) should drop only the self-loop; other destinations are still
    cut. Sink-side canonical placement puts the cut on the target's inbound
    edge.
    """
    edges = [("battery", "inv", "bat_inv"), ("inv", "load", "inv_load")]
    assert _min_cut_edges({"battery"}, {"battery", "load"}, edges) == {"inv_load"}


def test_min_cut_returns_empty_for_unreachable_destinations() -> None:
    """No s-t path in the subgraph means max flow is zero and cut is empty."""
    edges = [("a", "b", "ab"), ("c", "d", "cd")]
    assert _min_cut_edges({"a"}, {"d"}, edges) == set()


def test_min_cut_handles_parallel_edges() -> None:
    """Parallel edges share one aggregated flow; all parallel names are returned.

    If the aggregate edge between (u, v) is on the cut, every parallel
    connection between that pair is included.
    """
    edges = [
        ("grid", "load", "conn_a"),
        ("grid", "load", "conn_b"),
    ]
    assert _min_cut_edges({"grid"}, {"load"}, edges) == {"conn_a", "conn_b"}


def test_min_cut_scales_with_cardinality_not_capacity() -> None:
    """Unit capacities make the cut minimise placement cardinality.

    This matters for power-limit policies: the limit becomes a single sum
    over the cut (Σ cut-edge flow ≤ X), and minimum cardinality means the
    constraint has the fewest terms.
    """
    # Two independent paths from s to t, plus a three-hop scenic route.
    # Min cardinality cut = 2 (either both sources or both sinks).
    edges = [
        ("s", "a", "sa"),
        ("a", "t", "at"),
        ("s", "b", "sb"),
        ("b", "t", "bt"),
    ]
    cut = _min_cut_edges({"s"}, {"t"}, edges)
    assert len(cut) == 2


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
