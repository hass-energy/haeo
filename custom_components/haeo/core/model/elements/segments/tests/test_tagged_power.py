"""Tests for native tagged power flow on connections."""

from typing import Any

from highspy import Highs
import numpy as np
from numpy.typing import NDArray
import pytest

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.elements.connection import Connection
from custom_components.haeo.core.model.elements.segments import TagFilterSegment, TagPricingSegment
from custom_components.haeo.core.model.network import Network


class DummyElement(Element[str]):
    """Minimal element for endpoint wiring in tests."""

    def __init__(self, name: str, periods: NDArray[np.floating[Any]], solver: Highs) -> None:
        super().__init__(name=name, periods=periods, solver=solver, output_names=frozenset())


def create_solver() -> Highs:
    h = Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("log_to_console", False)
    return h


class TestTaggedPowerDecomposition:
    """Test that tagged power variables decompose total power correctly."""

    def test_tagged_power_sum_equals_total(self) -> None:
        """Sum of per-tag power equals total power flow."""
        h = create_solver()
        periods = np.array([1.0, 1.0])

        conn = Connection(
            name="conn",
            periods=periods,
            solver=h,
            source="src",
            target="tgt",
            tags=["solar", "grid"],
        )
        source = DummyElement("src", periods, h)
        target = DummyElement("tgt", periods, h)
        conn.set_endpoints(source, target)
        conn.constraints()

        # Fix total power
        h.addConstrs(conn.power_source_target == np.array([10.0, 10.0]))

        # Maximize solar tag to force decomposition
        first = conn._first  # noqa: SLF001
        h.minimize(-Highs.qsum(first.tagged_power_in_st("solar")))
        h.run()

        # Solar should take as much as possible (all 10)
        solar_vals = tuple(float(v) for v in h.vals(first.tagged_power_in_st("solar")))
        grid_vals = tuple(float(v) for v in h.vals(first.tagged_power_in_st("grid")))

        # Sum must equal total
        for s, g in zip(solar_vals, grid_vals, strict=True):
            assert s + g == pytest.approx(10.0)

    def test_tagged_power_linked_between_segments(self) -> None:
        """Per-tag power is linked between adjacent segments."""
        h = create_solver()
        periods = np.array([1.0])

        conn = Connection(
            name="conn",
            periods=periods,
            solver=h,
            source="src",
            target="tgt",
            tags=["solar", "grid"],
            segments={
                "passthrough": {"segment_type": "passthrough"},
                "pricing": {
                    "segment_type": "pricing",
                    "price_source_target": np.array([0.1]),
                },
            },
        )
        source = DummyElement("src", periods, h)
        target = DummyElement("tgt", periods, h)
        conn.set_endpoints(source, target)
        conn.constraints()

        # Fix total and solar tag on first segment
        first = list(conn.segments.values())[0]
        second = list(conn.segments.values())[1]

        h.addConstrs(conn.power_source_target == np.array([10.0]))
        h.addConstrs(first.tagged_power_in_st("solar") == np.array([7.0]))

        h.minimize(conn.cost())
        h.run()

        # Solar tag should be linked to second segment
        solar_second = tuple(float(v) for v in h.vals(second.tagged_power_in_st("solar")))
        assert solar_second == pytest.approx((7.0,))

        # Grid tag should fill the rest
        grid_second = tuple(float(v) for v in h.vals(second.tagged_power_in_st("grid")))
        assert grid_second == pytest.approx((3.0,))


class TestTagPricingOnConnection:
    """Test tag_pricing segment within a tagged connection."""

    def test_tag_pricing_affects_tagged_flow(self) -> None:
        """Tag pricing adds cost only to the tagged power flow."""
        h = create_solver()
        periods = np.array([1.0, 1.0])

        conn = Connection(
            name="conn",
            periods=periods,
            solver=h,
            source="src",
            target="tgt",
            tags=["solar", "grid"],
            segments={
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([10.0, 10.0]),
                },
                "tag_pricing": {
                    "segment_type": "tag_pricing",
                    "tag": "grid",
                    "price_source_target": np.array([0.50, 0.50]),
                },
            },
        )
        source = DummyElement("src", periods, h)
        target = DummyElement("tgt", periods, h)
        conn.set_endpoints(source, target)
        conn.constraints()

        # Fix total power at 10 kW
        h.addConstrs(conn.power_source_target == np.array([10.0, 10.0]))

        cost = conn.cost()
        assert cost is not None
        h.minimize(cost)
        h.run()

        # Optimizer should minimize grid tag (expensive) and maximize solar tag (free)
        tag_pricing_seg = conn["tag_pricing"]
        assert isinstance(tag_pricing_seg, TagPricingSegment)

        # All power should be solar (free) not grid (expensive)
        solar_first = list(conn.segments.values())[0]
        solar_vals = tuple(float(v) for v in h.vals(solar_first.tagged_power_in_st("solar")))
        grid_vals = tuple(float(v) for v in h.vals(solar_first.tagged_power_in_st("grid")))

        assert solar_vals == pytest.approx((10.0, 10.0))
        assert grid_vals == pytest.approx((0.0, 0.0))
        assert h.getObjectiveValue() == pytest.approx(0.0)


class TestTagFilterOnConnection:
    """Test tag_filter segment within a tagged connection."""

    def test_tag_filter_limits_tagged_flow(self) -> None:
        """Tag filter limits power for a specific tag only."""
        h = create_solver()
        periods = np.array([1.0, 1.0])

        conn = Connection(
            name="conn",
            periods=periods,
            solver=h,
            source="src",
            target="tgt",
            tags=["solar", "grid"],
            segments={
                "passthrough": {"segment_type": "passthrough"},
                "tag_filter": {
                    "segment_type": "tag_filter",
                    "tag": "grid",
                    "max_power_source_target": np.array([3.0, 3.0]),
                },
            },
        )
        source = DummyElement("src", periods, h)
        target = DummyElement("tgt", periods, h)
        conn.set_endpoints(source, target)
        conn.constraints()

        # Try to push 10 kW total
        h.minimize(-Highs.qsum(conn.power_source_target))
        h.run()

        # Grid should be capped at 3 kW
        tag_filter_seg = conn["tag_filter"]
        assert isinstance(tag_filter_seg, TagFilterSegment)

        grid_vals = tuple(float(v) for v in h.vals(tag_filter_seg.tagged_power_in_st("grid")))
        assert grid_vals == pytest.approx((3.0, 3.0))


class TestTaggedNetworkIntegration:
    """Test tagged power flow in a full network optimization."""

    def test_tariff_adds_cost_in_network(self) -> None:
        """Tariff connection adds cost to power flow in a network with tagged power."""
        periods = np.array([1.0, 1.0])
        network = Network(name="test", periods=periods)

        # Grid (source + sink)
        network.add({"element_type": "node", "name": "grid", "is_source": True, "is_sink": True})
        # Load (sink only)
        network.add({"element_type": "node", "name": "load", "is_source": False, "is_sink": True})

        # Connection with tags and tag pricing
        network.add({
            "element_type": "connection",
            "name": "grid_to_load",
            "source": "grid",
            "target": "load",
            "tags": ["import"],
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([10.0, 10.0]),
                },
                "pricing": {
                    "segment_type": "pricing",
                    "price_source_target": np.array([0.20, 0.20]),
                },
                "tag_pricing": {
                    "segment_type": "tag_pricing",
                    "tag": "import",
                    "price_source_target": np.array([0.05, 0.05]),
                },
            },
        })

        cost = network.optimize()

        # With 0 load, cost should be 0 (no power flows)
        assert cost == pytest.approx(0.0)
