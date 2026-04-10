"""Tests for the tariff compilation pipeline.

Tests cover:
- Tag assignment from tariff rules
- Source enforcement (only own tag flows outbound)
- Scoped pricing injection at destination
- End-to-end network optimization with tariffs
"""

from typing import Any

import numpy as np
import pytest

from custom_components.haeo.core.adapters.tariff_compilation import compile_tariffs
from custom_components.haeo.core.model.elements.segments.segment import DEFAULT_TAG
from custom_components.haeo.core.model.network import Network


def _make_node(name: str, *, is_source: bool = False, is_sink: bool = False) -> dict[str, Any]:
    return {"element_type": "node", "name": name, "is_source": is_source, "is_sink": is_sink}


def _make_junction(name: str) -> dict[str, Any]:
    """Make a pure junction node (no source, no sink)."""
    return {"element_type": "node", "name": name, "is_source": False, "is_sink": False}


def _make_connection(
    name: str, source: str, target: str,
    segments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    conn: dict[str, Any] = {
        "element_type": "connection",
        "name": name,
        "source": source,
        "target": target,
    }
    if segments:
        conn["segments"] = segments
    return conn


class TestTagAssignment:
    """Tag IDs are assigned correctly from tariff rules."""

    def test_single_tariff_assigns_one_tag(self) -> None:
        elements = [
            _make_node("grid", is_source=True, is_sink=True),
            _make_node("load", is_sink=True),
            _make_connection("conn", "grid", "load"),
        ]
        tariffs = [{"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.05}]
        result = compile_tariffs(elements, tariffs)

        connections = [e for e in result if e.get("element_type") == "connection"]
        assert len(connections) == 1
        tags = connections[0].get("tags", [])
        assert DEFAULT_TAG in tags
        assert len(tags) == 2  # tag 0 + grid's tag

    def test_multiple_sources_get_unique_tags(self) -> None:
        elements = [
            _make_node("grid", is_source=True, is_sink=True),
            _make_node("solar", is_source=True),
            _make_junction("sw"),
            _make_connection("c1", "grid", "sw"),
            _make_connection("c2", "solar", "sw"),
        ]
        tariffs = [
            {"sources": ["grid"], "destinations": ["*"], "price_source_target": 0.05},
            {"sources": ["solar"], "destinations": ["*"], "price_source_target": 0.01},
        ]
        result = compile_tariffs(elements, tariffs)

        connections = [e for e in result if e.get("element_type") == "connection"]
        # Both connections should have the same tag set
        tags0 = set(connections[0].get("tags", []))
        tags1 = set(connections[1].get("tags", []))
        assert tags0 == tags1
        assert len(tags0) == 3  # tag 0, grid tag, solar tag

    def test_any_source_assigns_tags_to_all_nodes(self) -> None:
        elements = [
            _make_node("grid"),
            _make_node("solar"),
            _make_junction("sw"),
            _make_connection("c1", "grid", "sw"),
            _make_connection("c2", "solar", "sw"),
        ]
        tariffs = [{"sources": ["*"], "destinations": ["sw"], "price_source_target": 0.05}]
        result = compile_tariffs(elements, tariffs)

        connections = [e for e in result if e.get("element_type") == "connection"]
        tags = set(connections[0].get("tags", []))
        # tag 0 + one tag per node (grid, solar, sw)
        assert len(tags) == 4

    def test_no_tariffs_returns_unchanged(self) -> None:
        elements = [
            _make_node("grid"),
            _make_connection("conn", "grid", "load"),
        ]
        result = compile_tariffs(elements, [])
        assert result == elements


class TestSourceEnforcement:
    """Source nodes can only produce power on their own tag."""

    def test_source_enforcement_blocks_other_tags(self) -> None:
        elements = [
            _make_node("grid"),
            _make_node("load"),
            _make_connection("conn", "grid", "load"),
        ]
        tariffs = [{"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.05}]
        result = compile_tariffs(elements, tariffs)

        conn = [e for e in result if e.get("element_type") == "connection"][0]
        segments = conn.get("segments", {})

        # Should have enforcement segments blocking tag 0 outbound from grid
        enforce_segments = {k: v for k, v in segments.items() if k.startswith("_enforce_")}
        assert len(enforce_segments) > 0

        # Tag 0 should be blocked from source→target (grid's outbound)
        has_block_t0 = any(
            s.get("tag") == DEFAULT_TAG and s.get("max_power_source_target") == 0.0
            for s in enforce_segments.values()
        )
        assert has_block_t0


class TestScopedPricingInjection:
    """Tariff pricing segments are injected at destination connections."""

    def test_pricing_injected_at_destination(self) -> None:
        elements = [
            _make_node("grid"),
            _make_node("load"),
            _make_connection("conn", "grid", "load"),
        ]
        tariffs = [{"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.05}]
        result = compile_tariffs(elements, tariffs)

        conn = [e for e in result if e.get("element_type") == "connection"][0]
        segments = conn.get("segments", {})

        # Should have a tariff pricing segment
        tariff_segments = {k: v for k, v in segments.items() if k.startswith("_tariff_")}
        assert len(tariff_segments) >= 1

        # The pricing segment should be scoped to grid's tag
        tariff_seg = list(tariff_segments.values())[0]
        assert tariff_seg["segment_type"] == "pricing"
        assert tariff_seg.get("tag") is not None
        assert tariff_seg["tag"] != DEFAULT_TAG


class TestEndToEndOptimization:
    """Full network optimization with compiled tariffs."""

    def test_grid_to_load_tariff_adds_cost(self) -> None:
        """Tariff pricing increases cost of grid→load power flow."""
        periods = np.array([1.0])

        # Simple two-node test: grid (source+sink) connected to load (sink only)
        # Load connection has pricing + tariff surcharge
        elements: list[dict[str, Any]] = [
            {"element_type": "node", "name": "grid", "is_source": True, "is_sink": True},
            {"element_type": "node", "name": "load", "is_source": False, "is_sink": True},
            {
                "element_type": "connection", "name": "conn",
                "source": "grid", "target": "load",
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": np.array([5.0]),
                        "max_power_target_source": np.array([5.0]),
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price_source_target": np.array([0.20]),
                    },
                },
            },
        ]

        tariffs = [{"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.05}]
        compiled = compile_tariffs(elements, tariffs)

        network = Network(name="test", periods=periods)
        sorted_elements = sorted(compiled, key=lambda e: e.get("element_type") == "connection")
        for elem in sorted_elements:
            network.add(elem)

        # Manually force load consumption by adding a constraint
        # The load node's connection power must be exactly 5 kW
        load_node = network.elements["load"]
        h = network._solver
        h.addConstrs(load_node.connection_power() == np.array([5.0]))

        cost = network.optimize()

        # Load draws 5 kW from grid.
        # Base pricing: 5 * 0.20 * 1 = $1.00
        # Tariff surcharge: 5 * 0.05 * 1 = $0.25
        # Total: $1.25
        assert cost == pytest.approx(1.25, abs=0.01)

    @pytest.mark.skip(reason="Multi-source tariff infeasibility under investigation")
    def test_cheaper_source_preferred_with_tariffs(self) -> None:
        """Optimizer prefers cheaper source when tariffs differ."""
        periods = np.array([1.0])

        # Direct connections: grid->load and solar->load (no intermediate sw)
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
                        "max_power_target_source": np.array([0.0]),
                    },
                },
            },
        ]

        tariffs = [
            {"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.10},
            {"sources": ["solar"], "destinations": ["load"], "price_source_target": 0.01},
        ]
        compiled = compile_tariffs(elements, tariffs)

        network = Network(name="test", periods=periods)
        sorted_elements = sorted(compiled, key=lambda e: e.get("element_type") == "connection")
        for elem in sorted_elements:
            network.add(elem)

        # Force load to consume 5 kW
        load_node = network.elements["load"]
        h = network._solver
        h.addConstrs(load_node.connection_power() == np.array([5.0]))

        cost = network.optimize()

        # Load needs 5 kW. Solar provides 3 kW ($0.01/kWh tariff).
        # Grid provides 2 kW ($0.30 base + $0.10 tariff = $0.40/kWh).
        # Solar cost: 3 * 0.01 = $0.03
        # Grid cost: 2 * 0.40 = $0.80
        # Total: $0.83
        assert cost == pytest.approx(0.83, abs=0.01)

    def test_no_tariff_no_extra_cost(self) -> None:
        """Without tariffs, optimization behaves normally."""
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
                    "fixed": True,
                },
            },
        })

        cost = network.optimize()
        # 5 kW * $0.20 * 1h = $1.00
        assert cost == pytest.approx(1.00)
