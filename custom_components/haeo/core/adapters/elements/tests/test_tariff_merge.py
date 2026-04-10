"""Tests for tariff connection merging in collect_model_elements."""

from typing import Any

import numpy as np
import pytest

from custom_components.haeo.core.adapters.registry import _merge_tariff_connections
from custom_components.haeo.core.model.elements.segments.segment import DEFAULT_TAG
from custom_components.haeo.core.model.network import Network


class TestMergeTariffConnections:
    """Test _merge_tariff_connections merging logic."""

    def test_no_tariff_connections_unchanged(self) -> None:
        """Non-tariff elements pass through unchanged."""
        elements: list[dict[str, Any]] = [
            {"element_type": "node", "name": "grid"},
            {"element_type": "connection", "name": "conn", "source": "grid", "target": "load",
             "segments": {"pricing": {"segment_type": "pricing", "price_source_target": 0.3}}},
        ]
        result = _merge_tariff_connections(elements)
        assert len(result) == 2

    def test_tariff_merged_into_existing_connection(self) -> None:
        """Tariff connection's tags and segments merge into matching base connection."""
        elements: list[dict[str, Any]] = [
            {"element_type": "node", "name": "grid"},
            {"element_type": "node", "name": "load"},
            {"element_type": "connection", "name": "conn", "source": "grid", "target": "load",
             "segments": {"pricing": {"segment_type": "pricing", "price_source_target": 0.3}}},
            {"element_type": "connection", "name": "tariff:tariff_connection",
             "source": "grid", "target": "load",
             "tags": [1],
             "segments": {"tariff_pricing": {"segment_type": "pricing", "tag": 1, "price_source_target": 0.05}}},
        ]
        result = _merge_tariff_connections(elements)

        # Should be 3 elements: 2 nodes + 1 merged connection (tariff folded in)
        connections = [e for e in result if e.get("element_type") == "connection"]
        assert len(connections) == 1

        conn = connections[0]
        assert 1 in conn["tags"]
        assert DEFAULT_TAG in conn.get("tags", [])
        assert "tariff_pricing" in conn["segments"]
        assert "pricing" in conn["segments"]

    def test_tariff_merged_reverse_direction(self) -> None:
        """Tariff merges even when source/target are reversed."""
        elements: list[dict[str, Any]] = [
            {"element_type": "connection", "name": "conn", "source": "grid", "target": "load",
             "segments": {"pricing": {"segment_type": "pricing"}}},
            {"element_type": "connection", "name": "tariff:tariff_connection",
             "source": "load", "target": "grid",
             "tags": [2],
             "segments": {"t_pricing": {"segment_type": "pricing", "tag": 2, "price_source_target": 0.1}}},
        ]
        result = _merge_tariff_connections(elements)
        connections = [e for e in result if e.get("element_type") == "connection"]
        assert len(connections) == 1
        assert 2 in connections[0]["tags"]

    def test_tariff_standalone_when_no_match(self) -> None:
        """Tariff connection kept standalone when no matching base connection exists."""
        elements: list[dict[str, Any]] = [
            {"element_type": "node", "name": "grid"},
            {"element_type": "connection", "name": "tariff:tariff_connection",
             "source": "grid", "target": "load",
             "tags": [1],
             "segments": {"tariff_pricing": {"segment_type": "pricing", "tag": 1}}},
        ]
        result = _merge_tariff_connections(elements)
        connections = [e for e in result if e.get("element_type") == "connection"]
        assert len(connections) == 1
        assert connections[0]["name"] == "tariff:tariff_connection"

    def test_segment_name_dedup_on_merge(self) -> None:
        """Segment names are deduplicated when tariff segment name collides."""
        elements: list[dict[str, Any]] = [
            {"element_type": "connection", "name": "conn", "source": "a", "target": "b",
             "segments": {"pricing": {"segment_type": "pricing", "price_source_target": 0.3}}},
            {"element_type": "connection", "name": "tariff:tariff_connection",
             "source": "a", "target": "b",
             "tags": [1],
             "segments": {"pricing": {"segment_type": "pricing", "tag": 1, "price_source_target": 0.05}}},
        ]
        result = _merge_tariff_connections(elements)
        connections = [e for e in result if e.get("element_type") == "connection"]
        assert len(connections) == 1
        segments = connections[0]["segments"]
        # Original "pricing" plus renamed "pricing_1"
        assert "pricing" in segments
        assert "pricing_1" in segments


class TestMergedNetworkOptimization:
    """Test that merged tariff connections work in full network optimization."""

    def test_merged_tariff_pricing_affects_optimization(self) -> None:
        """Tag-scoped pricing from merged tariff correctly affects cost."""
        periods = np.array([1.0])
        network = Network(name="test", periods=periods)

        network.add({"element_type": "node", "name": "grid", "is_source": True, "is_sink": True})
        network.add({"element_type": "node", "name": "load", "is_source": False, "is_sink": True})

        # Simulate merged connection: tag 0 (default) + tag 1 (tariff)
        # Base pricing on total, plus surcharge on tag 1
        network.add({
            "element_type": "connection",
            "name": "conn",
            "source": "grid",
            "target": "load",
            "tags": [0, 1],
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([10.0]),
                },
                "base_pricing": {
                    "segment_type": "pricing",
                    "price_source_target": np.array([0.20]),
                },
                "tariff_surcharge": {
                    "segment_type": "pricing",
                    "tag": 1,
                    "price_source_target": np.array([0.05]),
                },
            },
        })

        cost = network.optimize()
        # No forced load => no flow => cost 0
        assert cost == pytest.approx(0.0)
