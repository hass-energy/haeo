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

from typing import Any, cast

import numpy as np
import pytest

from custom_components.haeo.core.adapters.policy_compilation import compile_policies
from custom_components.haeo.core.model import ModelElementConfig, NetworkElement
from custom_components.haeo.core.model.network import Network


def _node(name: str, *, is_source: bool = False, is_sink: bool = False) -> dict[str, Any]:
    return {"element_type": "node", "name": name, "is_source": is_source, "is_sink": is_sink}


def _junction(name: str) -> dict[str, Any]:
    return {"element_type": "node", "name": name, "is_source": False, "is_sink": False}


def _conn(name: str, source: str, target: str, segments: dict[str, Any] | None = None) -> dict[str, Any]:
    c: dict[str, Any] = {"element_type": "connection", "name": name, "source": source, "target": target}
    if segments:
        c["segments"] = segments
    return c


def _connections(result: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in result if e.get("element_type") == "connection"]


def _find(result: list[dict[str, Any]], name: str) -> dict[str, Any]:
    return next(e for e in result if e.get("name") == name)


def _outbound_tag(result: list[dict[str, Any]], name: str) -> int:
    """Get the single outbound tag for a source node."""
    tags = _find(result, name)["outbound_tags"]
    assert len(tags) == 1
    return next(iter(tags))


def _network_element(network: Network, name: str) -> NetworkElement[Any]:
    """Get a network element with proper type narrowing."""
    elem = network.elements[name]
    assert isinstance(elem, NetworkElement)
    return elem


# --- Signature merging ---


def test_identical_prices_merge() -> None:
    """Grid and Solar with same price to Load share one VLAN."""
    elements = [_node("grid"), _node("solar"), _node("load"), _conn("c1", "grid", "load"), _conn("c2", "solar", "load")]
    policies = [
        {"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.05},
        {"sources": ["solar"], "destinations": ["load"], "price_source_target": 0.05},
    ]
    result = compile_policies(elements, policies)
    assert _outbound_tag(result, "grid") == _outbound_tag(result, "solar")


def test_different_prices_separate() -> None:
    """Grid and Solar with different prices get separate VLANs."""
    elements = [_node("grid"), _node("solar"), _node("load"), _conn("c1", "grid", "load"), _conn("c2", "solar", "load")]
    policies = [
        {"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.05},
        {"sources": ["solar"], "destinations": ["load"], "price_source_target": 0.02},
    ]
    result = compile_policies(elements, policies)
    assert _outbound_tag(result, "grid") != _outbound_tag(result, "solar")


def test_wildcard_all_same_merges() -> None:
    """Wildcard source with single policy -> all sources share one VLAN."""
    elements = [
        _node("a"),
        _node("b"),
        _node("c"),
        _node("d"),
        _conn("c1", "a", "d"),
        _conn("c2", "b", "d"),
        _conn("c3", "c", "d"),
    ]
    policies = [{"sources": ["*"], "destinations": ["d"], "price_source_target": 0.05}]
    result = compile_policies(elements, policies)
    assert _outbound_tag(result, "a") == _outbound_tag(result, "b") == _outbound_tag(result, "c")


def test_no_policies_no_vlans() -> None:
    """Without policies, elements pass through unchanged."""
    elements = [_node("grid"), _conn("c1", "grid", "load")]
    assert compile_policies(elements, []) == elements


def test_node_without_policy_gets_default() -> None:
    """Nodes not referenced by any policy stay on VLAN 0."""
    elements = [_node("grid"), _node("battery"), _node("load"), _conn("c1", "grid", "load")]
    policies = [{"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.05}]
    result = compile_policies(elements, policies)
    assert _find(result, "battery").get("outbound_tags") is None


# --- Reachability ---


def test_vlan_only_on_path() -> None:
    """VLAN only appears on connections between source and destination."""
    elements = [
        _node("grid"),
        _node("solar"),
        _junction("sw"),
        _node("load", is_sink=True),
        _conn("grid_sw", "grid", "sw"),
        _conn("solar_sw", "solar", "sw"),
        _conn("sw_load", "sw", "load"),
    ]
    policies = [{"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.05}]
    result = compile_policies(elements, policies)

    conns = {c["name"]: c for c in _connections(result)}
    grid_vlan = _outbound_tag(result, "grid")

    assert grid_vlan in conns["grid_sw"]["tags"]
    assert grid_vlan in conns["sw_load"]["tags"]
    assert grid_vlan not in conns["solar_sw"]["tags"]


# --- Access lists ---


def test_inbound_tags_set_on_destination() -> None:
    """Destination nodes get inbound tags from policies."""
    elements = [_node("grid"), _node("solar"), _node("load"), _conn("c1", "grid", "load"), _conn("c2", "solar", "load")]
    policies = [
        {"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.05},
        {"sources": ["solar"], "destinations": ["load"], "price_source_target": 0.02},
    ]
    result = compile_policies(elements, policies)

    load = _find(result, "load")
    grid_vlan = _outbound_tag(result, "grid")
    solar_vlan = _outbound_tag(result, "solar")
    assert grid_vlan in load["inbound_tags"]
    assert solar_vlan in load["inbound_tags"]


def test_no_inbound_tags_on_routing_nodes() -> None:
    """Routing nodes (not destinations) don't get inbound tags."""
    elements = [_node("grid"), _junction("sw"), _node("load"), _conn("c1", "grid", "sw"), _conn("c2", "sw", "load")]
    policies = [{"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.05}]
    result = compile_policies(elements, policies)
    assert _find(result, "sw").get("inbound_tags") is None


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
        {"sources": ["battery", "solar"], "destinations": ["load"], "price_source_target": 0.05},
        {"sources": ["battery"], "destinations": ["load"], "price_source_target": 0.03},
    ]
    compiled = compile_policies(elements, policies)

    # Battery and Solar should have different VLANs (different signatures)
    bat = _find(compiled, "battery")
    sol = _find(compiled, "solar")
    assert bat["outbound_tags"] != sol["outbound_tags"]

    # Build and optimize
    network = Network(name="test", periods=np.array([1.0]))
    for elem in sorted(compiled, key=lambda e: e.get("element_type") == "connection"):
        network.add(cast("ModelElementConfig", elem))

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
    policies = [{"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.10}]
    compiled = compile_policies(elements, policies)

    network = Network(name="test", periods=np.array([1.0]))
    for elem in sorted(compiled, key=lambda e: e.get("element_type") == "connection"):
        network.add(cast("ModelElementConfig", elem))

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
    policies = [{"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.10}]
    compiled = compile_policies(elements, policies)

    network = Network(name="test", periods=np.array([1.0]))
    for elem in sorted(compiled, key=lambda e: e.get("element_type") == "connection"):
        network.add(cast("ModelElementConfig", elem))
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
        {"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.10},
        {"sources": ["solar"], "destinations": ["load"], "price_source_target": 0.01},
    ]
    compiled = compile_policies(elements, policies)

    network = Network(name="test", periods=np.array([1.0]))
    for elem in sorted(compiled, key=lambda e: e.get("element_type") == "connection"):
        network.add(cast("ModelElementConfig", elem))
    h = network._solver
    h.addConstrs(_network_element(network, "load").connection_power() == np.array([5.0]))
    cost = network.optimize()

    # Solar 3 kW x $0.01 + Grid 2 kW x ($0.30 + $0.10)
    assert cost == pytest.approx(0.83, abs=0.01)


def test_no_policy_no_extra_cost() -> None:
    """Without policies, optimization behaves normally."""
    network = Network(name="test", periods=np.array([1.0]))
    network.add({"element_type": "node", "name": "grid", "is_source": True, "is_sink": True})
    network.add({"element_type": "node", "name": "load", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": "connection",
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
