"""Tests for native tagged power flow on connections.

All power is decomposed into integer tags (like VLANs).
Tag 0 is untagged/default. Segments can scope to specific tags or sets of tags.
"""

from typing import Any

from highspy import Highs
import numpy as np
from numpy.typing import NDArray
import pytest

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.elements.connection import Connection
from custom_components.haeo.core.model.elements.segments.segment import DEFAULT_TAG
from custom_components.haeo.core.model.network import Network


def _dummy_element(name: str, periods: NDArray[np.floating[Any]], solver: Highs) -> Element[str]:
    return Element(name=name, periods=periods, solver=solver, output_names=frozenset())


def _solver() -> Highs:
    h = Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("log_to_console", False)
    return h


# --- Default / single tag behavior ---


def test_default_tag_only() -> None:
    """Connection with no explicit tags has only DEFAULT_TAG."""
    h = _solver()
    periods = np.array([1.0])
    conn = Connection(name="c", periods=periods, solver=h, source="s", target="t")
    source = _dummy_element("s", periods, h)
    target = _dummy_element("t", periods, h)
    conn.set_endpoints(source, target)

    assert conn.connection_tags == [DEFAULT_TAG]
    first = next(iter(conn.segments.values()))
    assert first.tags == [DEFAULT_TAG]


def test_single_tag_optimization_unchanged() -> None:
    """Single tag behaves identically to the old untagged system."""
    periods = np.array([1.0, 1.0])
    network = Network(name="test", periods=periods)
    network.add({"element_type": "node", "name": "grid", "is_source": True, "is_sink": True})
    network.add({"element_type": "node", "name": "load", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": "connection",
            "name": "conn",
            "source": "grid",
            "target": "load",
            "segments": {"pricing": {"segment_type": "pricing", "price_source_target": np.array([0.30, 0.30])}},
        }
    )
    cost = network.optimize()
    assert cost == pytest.approx(0.0)


# --- Multi-tag decomposition ---


def test_tagged_power_sum_equals_total() -> None:
    """Sum of per-tag power equals total power flow."""
    h = _solver()
    periods = np.array([1.0, 1.0])
    conn = Connection(name="conn", periods=periods, solver=h, source="src", target="tgt", tags=[0, 1])
    source = _dummy_element("src", periods, h)
    target = _dummy_element("tgt", periods, h)
    conn.set_endpoints(source, target)
    conn.constraints()

    h.addConstrs(conn.power_source_target == np.array([10.0, 10.0]))
    first = next(iter(conn.segments.values()))
    h.minimize(-Highs.qsum(first.tag_power_in_st(1)))
    h.run()

    tag0 = tuple(float(v) for v in h.vals(first.tag_power_in_st(0)))
    tag1 = tuple(float(v) for v in h.vals(first.tag_power_in_st(1)))
    for t0, t1 in zip(tag0, tag1, strict=True):
        assert t0 + t1 == pytest.approx(10.0)


def test_per_tag_linked_between_segments() -> None:
    """Per-tag power is linked between adjacent segments."""
    h = _solver()
    periods = np.array([1.0])
    conn = Connection(
        name="conn",
        periods=periods,
        solver=h,
        source="src",
        target="tgt",
        tags=[0, 1],
        segments={
            "passthrough": {"segment_type": "passthrough"},
            "pricing": {"segment_type": "pricing", "price_source_target": np.array([0.1])},
        },
    )
    source = _dummy_element("src", periods, h)
    target = _dummy_element("tgt", periods, h)
    conn.set_endpoints(source, target)
    conn.constraints()

    first = next(iter(conn.segments.values()))
    second = list(conn.segments.values())[1]

    h.addConstrs(conn.power_source_target == np.array([10.0]))
    h.addConstrs(first.tag_power_in_st(1) == np.array([7.0]))
    h.minimize(conn.cost())
    h.run()

    tag1_second = tuple(float(v) for v in h.vals(second.tag_power_in_st(1)))
    assert tag1_second == pytest.approx((7.0,))

    tag0_second = tuple(float(v) for v in h.vals(second.tag_power_in_st(0)))
    assert tag0_second == pytest.approx((3.0,))


# --- Scoped segments ---


def test_scoped_pricing_only_charges_tagged_flow() -> None:
    """Pricing with tag=1 only charges tag 1's power, not tag 0."""
    h = _solver()
    periods = np.array([1.0, 1.0])
    conn = Connection(
        name="conn",
        periods=periods,
        solver=h,
        source="src",
        target="tgt",
        tags=[0, 1],
        segments={
            "power_limit": {"segment_type": "power_limit", "max_power_source_target": np.array([10.0, 10.0])},
            "scoped_pricing": {"segment_type": "pricing", "tag": 1, "price_source_target": np.array([0.50, 0.50])},
        },
    )
    source = _dummy_element("src", periods, h)
    target = _dummy_element("tgt", periods, h)
    conn.set_endpoints(source, target)
    conn.constraints()

    h.addConstrs(conn.power_source_target == np.array([10.0, 10.0]))
    cost = conn.cost()
    assert cost is not None
    h.minimize(cost)
    h.run()

    first = next(iter(conn.segments.values()))
    tag0 = tuple(float(v) for v in h.vals(first.tag_power_in_st(0)))
    tag1 = tuple(float(v) for v in h.vals(first.tag_power_in_st(1)))
    assert tag0 == pytest.approx((10.0, 10.0))
    assert tag1 == pytest.approx((0.0, 0.0))
    assert h.getObjectiveValue() == pytest.approx(0.0)


def test_scoped_limit_only_constrains_tagged_flow() -> None:
    """Power limit with tag=1 limits only tag 1, not the total."""
    h = _solver()
    periods = np.array([1.0, 1.0])
    conn = Connection(
        name="conn",
        periods=periods,
        solver=h,
        source="src",
        target="tgt",
        tags=[0, 1],
        segments={
            "passthrough": {"segment_type": "passthrough"},
            "tag1_limit": {"segment_type": "power_limit", "tag": 1, "max_power_source_target": np.array([3.0, 3.0])},
        },
    )
    source = _dummy_element("src", periods, h)
    target = _dummy_element("tgt", periods, h)
    conn.set_endpoints(source, target)
    conn.constraints()

    h.minimize(-Highs.qsum(conn.power_source_target))
    h.run()

    first = next(iter(conn.segments.values()))
    tag1 = tuple(float(v) for v in h.vals(first.tag_power_in_st(1)))
    assert tag1 == pytest.approx((3.0, 3.0))


# --- Multi-tag scoping (group constraints) ---


def test_multi_tag_power_limit() -> None:
    """Power limit scoped to tags {1,2} constrains their sum."""
    h = _solver()
    periods = np.array([1.0])
    conn = Connection(
        name="conn",
        periods=periods,
        solver=h,
        source="src",
        target="tgt",
        tags=[0, 1, 2],
        segments={
            "total_limit": {"segment_type": "power_limit", "max_power_source_target": np.array([7.0])},
            "group_limit": {"segment_type": "power_limit", "tag": [1, 2], "max_power_source_target": np.array([5.0])},
            "individual_limit": {"segment_type": "power_limit", "tag": 2, "max_power_source_target": np.array([2.0])},
        },
    )
    source = _dummy_element("src", periods, h)
    target = _dummy_element("tgt", periods, h)
    conn.set_endpoints(source, target)
    conn.constraints()

    h.minimize(-Highs.qsum(conn.power_source_target))
    h.run()

    first = next(iter(conn.segments.values()))
    tag0 = float(h.vals(first.tag_power_in_st(0))[0])
    tag1 = float(h.vals(first.tag_power_in_st(1))[0])
    tag2 = float(h.vals(first.tag_power_in_st(2))[0])

    # Verify constraints hold
    assert tag1 + tag2 <= 5.0 + 0.01  # Group limit
    assert tag2 <= 2.0 + 0.01  # Individual limit


def test_multi_tag_pricing_adds_combined_cost() -> None:
    """Pricing scoped to tags {1,2} prices their combined flow."""
    h = _solver()
    periods = np.array([1.0])
    conn = Connection(
        name="conn",
        periods=periods,
        solver=h,
        source="src",
        target="tgt",
        tags=[0, 1, 2],
        segments={
            "passthrough": {"segment_type": "passthrough"},
            "group_pricing": {"segment_type": "pricing", "tag": [1, 2], "price_source_target": np.array([0.10])},
        },
    )
    source = _dummy_element("src", periods, h)
    target = _dummy_element("tgt", periods, h)
    conn.set_endpoints(source, target)
    conn.constraints()

    first = next(iter(conn.segments.values()))
    h.addConstrs(first.tag_power_in_st(0) == np.array([1.0]))
    h.addConstrs(first.tag_power_in_st(1) == np.array([3.0]))
    h.addConstrs(first.tag_power_in_st(2) == np.array([2.0]))

    cost = conn.cost()
    assert cost is not None
    h.minimize(cost)
    h.run()

    assert h.getObjectiveValue() == pytest.approx(0.50, abs=0.01)


# --- Efficiency with tags ---


def test_efficiency_applies_per_tag() -> None:
    """Efficiency segment reduces each tag's output independently."""
    h = _solver()
    periods = np.array([1.0])
    conn = Connection(
        name="conn",
        periods=periods,
        solver=h,
        source="src",
        target="tgt",
        tags=[0, 1],
        segments={
            "efficiency": {
                "segment_type": "efficiency",
                "efficiency_source_target": np.array([0.90]),
            },
        },
    )
    source = _dummy_element("src", periods, h)
    target = _dummy_element("tgt", periods, h)
    conn.set_endpoints(source, target)
    conn.constraints()

    seg = next(iter(conn.segments.values()))
    h.addConstrs(seg.tag_power_in_st(0) == np.array([10.0]))
    h.addConstrs(seg.tag_power_in_st(1) == np.array([5.0]))
    h.run()

    tag0_out = float(h.vals(seg.tag_power_out_st(0))[0])
    tag1_out = float(h.vals(seg.tag_power_out_st(1))[0])
    assert tag0_out == pytest.approx(9.0)
    assert tag1_out == pytest.approx(4.5)

    total_out = float(h.vals(conn.power_source_target)[0])
    assert total_out == pytest.approx(15.0)  # total input, not output


# --- Tagged power outputs ---


def test_tagged_power_output_contains_per_tag_flows() -> None:
    """Connection outputs include tagged_power map when tags > 1."""
    h = _solver()
    periods = np.array([1.0])
    conn = Connection(name="conn", periods=periods, solver=h, source="src", target="tgt", tags=[0, 1])
    source = _dummy_element("src", periods, h)
    target = _dummy_element("tgt", periods, h)
    conn.set_endpoints(source, target)
    conn.constraints()

    first = next(iter(conn.segments.values()))
    h.addConstrs(first.tag_power_in_st(0) == np.array([7.0]))
    h.addConstrs(first.tag_power_in_st(1) == np.array([3.0]))
    h.run()

    outputs = conn.outputs()
    assert "connection_tagged_power" in outputs
    tagged = outputs["connection_tagged_power"]
    assert 0 in tagged
    assert 1 in tagged
    assert tagged[0]["source_target"].values == pytest.approx((7.0,))
    assert tagged[1]["source_target"].values == pytest.approx((3.0,))


def test_single_tag_omits_tagged_output() -> None:
    """Single-tag connections don't include tagged_power output."""
    h = _solver()
    periods = np.array([1.0])
    conn = Connection(name="conn", periods=periods, solver=h, source="src", target="tgt")
    source = _dummy_element("src", periods, h)
    target = _dummy_element("tgt", periods, h)
    conn.set_endpoints(source, target)
    conn.constraints()
    h.run()

    outputs = conn.outputs()
    assert "connection_tagged_power" not in outputs


# --- Network integration ---


def test_tags_with_pricing_in_network() -> None:
    """Network with tagged connection and scoped pricing optimizes correctly."""
    periods = np.array([1.0, 1.0])
    network = Network(name="test", periods=periods)
    network.add({"element_type": "node", "name": "grid", "is_source": True, "is_sink": True})
    network.add({"element_type": "node", "name": "load", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": "connection",
            "name": "conn",
            "source": "grid",
            "target": "load",
            "tags": [0, 1],
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power_source_target": np.array([10.0, 10.0])},
                "base_pricing": {"segment_type": "pricing", "price_source_target": np.array([0.20, 0.20])},
                "surcharge": {"segment_type": "pricing", "tag": 1, "price_source_target": np.array([0.05, 0.05])},
            },
        }
    )
    cost = network.optimize()
    assert cost == pytest.approx(0.0)


def test_source_tag_enforcement_in_network() -> None:
    """source_tag on a node ensures net outbound power is on the source tag."""
    periods = np.array([1.0])
    network = Network(name="test", periods=periods)
    network.add({"element_type": "node", "name": "grid", "is_source": True, "is_sink": True, "source_tag": 1})
    network.add({"element_type": "node", "name": "load", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": "connection",
            "name": "conn",
            "source": "grid",
            "target": "load",
            "tags": [0, 1],
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([10.0]),
                    "max_power_target_source": np.array([10.0]),
                },
                "pricing": {"segment_type": "pricing", "tag": 1, "price_source_target": np.array([0.10])},
            },
        }
    )

    h = network._solver
    h.addConstrs(network.elements["load"].connection_power() == np.array([5.0]))
    cost = network.optimize()

    # Grid produces 5 kW net. With source_tag=1, the net outbound flow
    # must be on tag 1. Tag 1 pricing: 5 x $0.10 = $0.50
    assert cost == pytest.approx(0.50, abs=0.01)
