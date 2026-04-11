"""Tests for the optimized policy compilation pipeline.

Tests cover:
- Signature-based VLAN merging (minimum tag count)
- Reachability pruning (per-connection tag sets)
- Node access lists
- Source enforcement
- End-to-end network optimization with policies
"""

from typing import Any

import numpy as np
import pytest

from custom_components.haeo.core.adapters.tariff_compilation import compile_policies
from custom_components.haeo.core.model.elements.segments.segment import DEFAULT_TAG
from custom_components.haeo.core.model.network import Network


def _make_node(name: str, *, is_source: bool = False, is_sink: bool = False) -> dict[str, Any]:
    return {"element_type": "node", "name": name, "is_source": is_source, "is_sink": is_sink}


def _make_junction(name: str) -> dict[str, Any]:
    return {"element_type": "node", "name": name, "is_source": False, "is_sink": False}


def _make_connection(
    name: str, source: str, target: str,
    segments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    conn: dict[str, Any] = {"element_type": "connection", "name": name, "source": source, "target": target}
    if segments:
        conn["segments"] = segments
    return conn


def _get_connections(result: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in result if e.get("element_type") == "connection"]


def _get_node(result: list[dict[str, Any]], name: str) -> dict[str, Any]:
    return next(e for e in result if e.get("name") == name and e.get("element_type") == "node")


class TestSignatureMerging:
    """Sources with identical policy signatures share a VLAN."""

    def test_identical_prices_merge(self) -> None:
        """Grid and Solar with same price to Load share one VLAN."""
        elements = [
            _make_node("grid"), _make_node("solar"), _make_node("load"),
            _make_connection("c1", "grid", "load"),
            _make_connection("c2", "solar", "load"),
        ]
        policies = [
            {"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.05},
            {"sources": ["solar"], "destinations": ["load"], "price_source_target": 0.05},
        ]
        result = compile_policies(elements, policies)

        grid = _get_node(result, "grid")
        solar = _get_node(result, "solar")
        # Same signature → same VLAN
        assert grid["source_tag"] == solar["source_tag"]

        # Only 2 VLANs total (default + merged)
        conns = _get_connections(result)
        all_tags = set()
        for c in conns:
            all_tags.update(c.get("tags", []))
        assert len(all_tags) == 2

    def test_different_prices_separate(self) -> None:
        """Grid and Solar with different prices get separate VLANs."""
        elements = [
            _make_node("grid"), _make_node("solar"), _make_node("load"),
            _make_connection("c1", "grid", "load"),
            _make_connection("c2", "solar", "load"),
        ]
        policies = [
            {"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.05},
            {"sources": ["solar"], "destinations": ["load"], "price_source_target": 0.02},
        ]
        result = compile_policies(elements, policies)

        grid = _get_node(result, "grid")
        solar = _get_node(result, "solar")
        assert grid["source_tag"] != solar["source_tag"]

    def test_wildcard_all_same_merges(self) -> None:
        """Wildcard source with single policy → all sources share one VLAN."""
        elements = [
            _make_node("grid"), _make_node("solar"), _make_node("battery"), _make_node("load"),
            _make_connection("c1", "grid", "load"),
            _make_connection("c2", "solar", "load"),
            _make_connection("c3", "battery", "load"),
        ]
        policies = [{"sources": ["*"], "destinations": ["load"], "price_source_target": 0.05}]
        result = compile_policies(elements, policies)

        grid = _get_node(result, "grid")
        solar = _get_node(result, "solar")
        battery = _get_node(result, "battery")
        # All three share the same VLAN
        assert grid["source_tag"] == solar["source_tag"] == battery["source_tag"]

    def test_no_policies_no_vlans(self) -> None:
        """Without policies, elements pass through unchanged."""
        elements = [
            _make_node("grid"), _make_connection("c1", "grid", "load"),
        ]
        result = compile_policies(elements, [])
        assert result == elements

    def test_node_without_policy_gets_default(self) -> None:
        """Nodes not referenced by any policy stay on VLAN 0."""
        elements = [
            _make_node("grid"), _make_node("solar"), _make_node("battery"), _make_node("load"),
            _make_connection("c1", "grid", "load"),
        ]
        policies = [{"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.05}]
        result = compile_policies(elements, policies)

        battery = _get_node(result, "battery")
        assert battery.get("source_tag") is None  # No source_tag for default


class TestReachability:
    """VLANs only appear on connections in the path from source to destination."""

    def test_vlan_only_on_path(self) -> None:
        """VLAN only appears on connections between source and destination."""
        elements = [
            _make_node("grid"), _make_node("solar"),
            _make_junction("sw"),
            _make_node("load", is_sink=True),
            _make_connection("grid_sw", "grid", "sw"),
            _make_connection("solar_sw", "solar", "sw"),
            _make_connection("sw_load", "sw", "load"),
        ]
        policies = [{"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.05}]
        result = compile_policies(elements, policies)

        conns = {c["name"]: c for c in _get_connections(result)}
        grid_vlan = _get_node(result, "grid")["source_tag"]

        # Grid VLAN on the path: grid→sw and sw→load
        assert grid_vlan in conns["grid_sw"]["tags"]
        assert grid_vlan in conns["sw_load"]["tags"]
        # Grid VLAN NOT on solar→sw (not on the path)
        assert grid_vlan not in conns["solar_sw"]["tags"]


class TestNodeAccessLists:
    """Nodes can only consume VLANs from their access list."""

    def test_access_list_set_on_destination(self) -> None:
        """Destination nodes get access lists from policies."""
        elements = [
            _make_node("grid"), _make_node("solar"), _make_node("load"),
            _make_connection("c1", "grid", "load"),
            _make_connection("c2", "solar", "load"),
        ]
        policies = [
            {"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.05},
            {"sources": ["solar"], "destinations": ["load"], "price_source_target": 0.02},
        ]
        result = compile_policies(elements, policies)

        load = _get_node(result, "load")
        grid_vlan = _get_node(result, "grid")["source_tag"]
        solar_vlan = _get_node(result, "solar")["source_tag"]

        assert "access_list" in load
        assert grid_vlan in load["access_list"]
        assert solar_vlan in load["access_list"]

    def test_no_access_list_on_unaffected_nodes(self) -> None:
        """Nodes not destinations in any policy don't get access lists."""
        elements = [
            _make_node("grid"), _make_junction("sw"), _make_node("load"),
            _make_connection("c1", "grid", "sw"),
            _make_connection("c2", "sw", "load"),
        ]
        policies = [{"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.05}]
        result = compile_policies(elements, policies)

        sw = _get_node(result, "sw")
        assert sw.get("access_list") is None


class TestEndToEndOptimization:
    """Full network optimization with compiled policies."""

    def test_single_source_policy_adds_cost(self) -> None:
        """Policy pricing adds cost to power flow."""
        periods = np.array([1.0])
        elements: list[dict[str, Any]] = [
            {"element_type": "node", "name": "grid", "is_source": True, "is_sink": True},
            {"element_type": "node", "name": "load", "is_source": False, "is_sink": True},
            {
                "element_type": "connection", "name": "conn",
                "source": "grid", "target": "load",
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": np.array([10.0]),
                        "max_power_target_source": np.array([10.0]),
                    },
                },
            },
        ]
        policies = [{"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.10}]
        compiled = compile_policies(elements, policies)

        network = Network(name="test", periods=periods)
        for elem in sorted(compiled, key=lambda e: e.get("element_type") == "connection"):
            network.add(elem)

        h = network._solver
        h.addConstrs(network.elements["load"].connection_power() == np.array([5.0]))

        cost = network.optimize()
        assert cost == pytest.approx(0.50, abs=0.01)  # 5 kW × $0.10

    def test_cheaper_source_preferred(self) -> None:
        """Optimizer uses cheaper source when policies differentiate."""
        periods = np.array([1.0])
        elements: list[dict[str, Any]] = [
            {"element_type": "node", "name": "grid", "is_source": True, "is_sink": True},
            {"element_type": "node", "name": "solar", "is_source": True, "is_sink": False},
            {"element_type": "node", "name": "load", "is_source": False, "is_sink": True},
            {
                "element_type": "connection", "name": "grid_conn",
                "source": "grid", "target": "load",
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": np.array([10.0]),
                        "max_power_target_source": np.array([10.0]),
                    },
                    "pricing": {"segment_type": "pricing", "price_source_target": np.array([0.30])},
                },
            },
            {
                "element_type": "connection", "name": "solar_conn",
                "source": "solar", "target": "load",
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": np.array([3.0]),
                        "max_power_target_source": np.array([3.0]),
                    },
                },
            },
        ]
        policies = [
            {"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.10},
            {"sources": ["solar"], "destinations": ["load"], "price_source_target": 0.01},
        ]
        compiled = compile_policies(elements, policies)

        network = Network(name="test", periods=periods)
        for elem in sorted(compiled, key=lambda e: e.get("element_type") == "connection"):
            network.add(elem)

        h = network._solver
        h.addConstrs(network.elements["load"].connection_power() == np.array([5.0]))

        cost = network.optimize()
        # Solar: 3 kW × $0.01 = $0.03
        # Grid: 2 kW × ($0.30 + $0.10) = $0.80
        # Total: $0.83
        assert cost == pytest.approx(0.83, abs=0.01)

    def test_no_policy_no_extra_cost(self) -> None:
        """Without policies, optimization behaves normally."""
        periods = np.array([1.0])
        network = Network(name="test", periods=periods)

        network.add({"element_type": "node", "name": "grid", "is_source": True, "is_sink": True})
        network.add({"element_type": "node", "name": "load", "is_source": False, "is_sink": True})
        network.add({
            "element_type": "connection", "name": "conn",
            "source": "grid", "target": "load",
            "segments": {
                "pricing": {"segment_type": "pricing", "price_source_target": np.array([0.20])},
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([5.0]),
                    "max_power_target_source": np.array([5.0]),
                },
            },
        })

        h = network._solver
        h.addConstrs(network.elements["load"].connection_power() == np.array([5.0]))

        cost = network.optimize()
        assert cost == pytest.approx(1.00)  # 5 kW × $0.20
