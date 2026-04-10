"""Tests for native tagged power flow on connections.

All power is decomposed into integer tags (like VLANs).
Tag 0 is untagged/default. Segments can scope to specific tags.
"""

from typing import Any

from highspy import Highs
import numpy as np
from numpy.typing import NDArray
import pytest

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.elements.connection import Connection
from custom_components.haeo.core.model.elements.segments import PricingSegment, PowerLimitSegment
from custom_components.haeo.core.model.elements.segments.segment import DEFAULT_TAG
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


class TestSingleTagDefault:
    """With no explicit tags, connections use tag 0 only."""

    def test_default_tag_only(self) -> None:
        """Connection with no tags has only DEFAULT_TAG."""
        h = create_solver()
        periods = np.array([1.0])
        conn = Connection(name="c", periods=periods, solver=h, source="s", target="t")
        source = DummyElement("s", periods, h)
        target = DummyElement("t", periods, h)
        conn.set_endpoints(source, target)

        assert conn.connection_tags == [DEFAULT_TAG]
        # power_in_st should work (returns tag 0's variable)
        first = list(conn.segments.values())[0]
        assert first.tags == [DEFAULT_TAG]

    def test_single_tag_optimization_unchanged(self) -> None:
        """Single tag behaves identically to the old untagged system."""
        periods = np.array([1.0, 1.0])
        network = Network(name="test", periods=periods)

        network.add({"element_type": "node", "name": "grid", "is_source": True, "is_sink": True})
        network.add({"element_type": "node", "name": "load", "is_source": False, "is_sink": True})
        network.add({
            "element_type": "connection",
            "name": "conn",
            "source": "grid",
            "target": "load",
            "segments": {
                "pricing": {
                    "segment_type": "pricing",
                    "price_source_target": np.array([0.30, 0.30]),
                },
            },
        })

        cost = network.optimize()
        # No load, no forced flow => cost should be 0
        assert cost == pytest.approx(0.0)


class TestMultiTagDecomposition:
    """Test that tagged power decomposes correctly across multiple tags."""

    def test_tagged_power_sum_equals_total(self) -> None:
        """Sum of per-tag power equals total power flow."""
        h = create_solver()
        periods = np.array([1.0, 1.0])

        conn = Connection(
            name="conn", periods=periods, solver=h,
            source="src", target="tgt",
            tags=[0, 1],  # tag 0 (default) + tag 1
        )
        source = DummyElement("src", periods, h)
        target = DummyElement("tgt", periods, h)
        conn.set_endpoints(source, target)
        conn.constraints()

        # Fix total power
        h.addConstrs(conn.power_source_target == np.array([10.0, 10.0]))

        # Maximize tag 1 flow to force decomposition
        first = list(conn.segments.values())[0]
        h.minimize(-Highs.qsum(first.tag_power_in_st(1)))
        h.run()

        tag0 = tuple(float(v) for v in h.vals(first.tag_power_in_st(0)))
        tag1 = tuple(float(v) for v in h.vals(first.tag_power_in_st(1)))

        for t0, t1 in zip(tag0, tag1, strict=True):
            assert t0 + t1 == pytest.approx(10.0)

    def test_per_tag_linked_between_segments(self) -> None:
        """Per-tag power is linked between adjacent segments."""
        h = create_solver()
        periods = np.array([1.0])

        conn = Connection(
            name="conn", periods=periods, solver=h,
            source="src", target="tgt",
            tags=[0, 1],
            segments={
                "passthrough": {"segment_type": "passthrough"},
                "pricing": {"segment_type": "pricing", "price_source_target": np.array([0.1])},
            },
        )
        source = DummyElement("src", periods, h)
        target = DummyElement("tgt", periods, h)
        conn.set_endpoints(source, target)
        conn.constraints()

        first = list(conn.segments.values())[0]
        second = list(conn.segments.values())[1]

        # Fix total and tag 1 on first segment
        h.addConstrs(conn.power_source_target == np.array([10.0]))
        h.addConstrs(first.tag_power_in_st(1) == np.array([7.0]))

        h.minimize(conn.cost())
        h.run()

        # Tag 1 should be linked to second segment
        tag1_second = tuple(float(v) for v in h.vals(second.tag_power_in_st(1)))
        assert tag1_second == pytest.approx((7.0,))

        # Tag 0 fills the rest
        tag0_second = tuple(float(v) for v in h.vals(second.tag_power_in_st(0)))
        assert tag0_second == pytest.approx((3.0,))


class TestScopedPricing:
    """Test pricing segment scoped to a specific tag."""

    def test_scoped_pricing_only_charges_tagged_flow(self) -> None:
        """Pricing with tag=1 only charges tag 1's power, not tag 0."""
        h = create_solver()
        periods = np.array([1.0, 1.0])

        conn = Connection(
            name="conn", periods=periods, solver=h,
            source="src", target="tgt",
            tags=[0, 1],
            segments={
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([10.0, 10.0]),
                },
                "scoped_pricing": {
                    "segment_type": "pricing",
                    "tag": 1,
                    "price_source_target": np.array([0.50, 0.50]),
                },
            },
        )
        source = DummyElement("src", periods, h)
        target = DummyElement("tgt", periods, h)
        conn.set_endpoints(source, target)
        conn.constraints()

        # Fix total power
        h.addConstrs(conn.power_source_target == np.array([10.0, 10.0]))

        cost = conn.cost()
        assert cost is not None
        h.minimize(cost)
        h.run()

        # Optimizer minimizes cost: all power goes to tag 0 (free), none to tag 1 (expensive)
        first = list(conn.segments.values())[0]
        tag0 = tuple(float(v) for v in h.vals(first.tag_power_in_st(0)))
        tag1 = tuple(float(v) for v in h.vals(first.tag_power_in_st(1)))

        assert tag0 == pytest.approx((10.0, 10.0))
        assert tag1 == pytest.approx((0.0, 0.0))
        assert h.getObjectiveValue() == pytest.approx(0.0)


class TestScopedPowerLimit:
    """Test power limit segment scoped to a specific tag."""

    def test_scoped_limit_only_constrains_tagged_flow(self) -> None:
        """Power limit with tag=1 limits only tag 1, not the total."""
        h = create_solver()
        periods = np.array([1.0, 1.0])

        conn = Connection(
            name="conn", periods=periods, solver=h,
            source="src", target="tgt",
            tags=[0, 1],
            segments={
                "passthrough": {"segment_type": "passthrough"},
                "tag1_limit": {
                    "segment_type": "power_limit",
                    "tag": 1,
                    "max_power_source_target": np.array([3.0, 3.0]),
                },
            },
        )
        source = DummyElement("src", periods, h)
        target = DummyElement("tgt", periods, h)
        conn.set_endpoints(source, target)
        conn.constraints()

        # Maximize total flow — tag 1 limited to 3, tag 0 unconstrained
        h.minimize(-Highs.qsum(conn.power_source_target))
        h.run()

        first = list(conn.segments.values())[0]
        tag1 = tuple(float(v) for v in h.vals(first.tag_power_in_st(1)))
        assert tag1 == pytest.approx((3.0, 3.0))


class TestNetworkIntegrationWithTags:
    """Test tagged power in full network optimizations."""

    def test_tags_with_pricing_in_network(self) -> None:
        """Network with tagged connection and scoped pricing optimizes correctly."""
        periods = np.array([1.0, 1.0])
        network = Network(name="test", periods=periods)

        network.add({"element_type": "node", "name": "grid", "is_source": True, "is_sink": True})
        network.add({"element_type": "node", "name": "load", "is_source": False, "is_sink": True})

        network.add({
            "element_type": "connection",
            "name": "grid_to_load",
            "source": "grid",
            "target": "load",
            "tags": [0, 1],
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([10.0, 10.0]),
                },
                "base_pricing": {
                    "segment_type": "pricing",
                    "price_source_target": np.array([0.20, 0.20]),
                },
                "surcharge": {
                    "segment_type": "pricing",
                    "tag": 1,
                    "price_source_target": np.array([0.05, 0.05]),
                },
            },
        })

        cost = network.optimize()
        # No load → no forced flow → cost 0
        assert cost == pytest.approx(0.0)


class TestTaggedPowerOutputs:
    """Test that connection outputs include per-tag power decomposition."""

    def test_tagged_power_output_contains_per_tag_flows(self) -> None:
        """Connection outputs include tagged_power map when tags > 1."""
        h = create_solver()
        periods = np.array([1.0])

        conn = Connection(
            name="conn", periods=periods, solver=h,
            source="src", target="tgt",
            tags=[0, 1],
        )
        source = DummyElement("src", periods, h)
        target = DummyElement("tgt", periods, h)
        conn.set_endpoints(source, target)
        conn.constraints()

        # Fix flow: 10 kW st, split 7/3 between tags
        first = list(conn.segments.values())[0]
        h.addConstrs(first.tag_power_in_st(0) == np.array([7.0]))
        h.addConstrs(first.tag_power_in_st(1) == np.array([3.0]))
        h.run()

        outputs = conn.outputs()
        assert "connection_tagged_power" in outputs

        tagged = outputs["connection_tagged_power"]
        assert isinstance(tagged, dict)
        assert 0 in tagged
        assert 1 in tagged

        # Tag 0: 7 kW st
        tag0_st = tagged[0]["source_target"]
        assert tag0_st.values == pytest.approx((7.0,))

        # Tag 1: 3 kW st
        tag1_st = tagged[1]["source_target"]
        assert tag1_st.values == pytest.approx((3.0,))

    def test_single_tag_omits_tagged_output(self) -> None:
        """Single-tag connections don't include tagged_power output."""
        h = create_solver()
        periods = np.array([1.0])

        conn = Connection(
            name="conn", periods=periods, solver=h,
            source="src", target="tgt",
        )
        source = DummyElement("src", periods, h)
        target = DummyElement("tgt", periods, h)
        conn.set_endpoints(source, target)
        conn.constraints()
        h.run()

        outputs = conn.outputs()
        assert "connection_tagged_power" not in outputs
