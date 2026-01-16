"""Tests for connection segments and Connection class."""

from collections.abc import Sequence
from typing import Literal, TypedDict

from highspy import Highs
import numpy as np
import pytest

from custom_components.haeo.model.elements.connection import Connection
from custom_components.haeo.model.elements.segments import (
    EfficiencySegment,
    PassthroughSegment,
    PowerLimitSegment,
    PricingSegment,
    SegmentSpec,
)


def create_solver() -> Highs:
    """Create a silent HiGHS solver."""
    h = Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("log_to_console", False)
    return h


class SegmentIdentityCase(TypedDict):
    """Case describing segment in/out variable identity."""

    description: str
    factory: type
    spec: SegmentSpec
    expect_same: bool


SEGMENT_IDENTITY_CASES: Sequence[SegmentIdentityCase] = [
    {
        "description": "Passthrough segment uses same in/out variables",
        "factory": PassthroughSegment,
        "spec": {"segment_type": "passthrough"},
        "expect_same": True,
    },
    {
        "description": "Efficiency segment uses separate in/out variables",
        "factory": EfficiencySegment,
        "spec": {"segment_type": "efficiency", "efficiency_source_target": np.array([0.9, 0.9])},
        "expect_same": False,
    },
    {
        "description": "Power limit segment uses same in/out variables",
        "factory": PowerLimitSegment,
        "spec": {"segment_type": "power_limit", "max_power_source_target": np.array([5.0, 5.0])},
        "expect_same": True,
    },
    {
        "description": "Pricing segment uses same in/out variables",
        "factory": PricingSegment,
        "spec": {"segment_type": "pricing", "price_source_target": np.array([0.1, 0.1])},
        "expect_same": True,
    },
]


@pytest.mark.parametrize("case", SEGMENT_IDENTITY_CASES, ids=lambda c: c["description"])
def test_segment_in_out_identity(case: SegmentIdentityCase) -> None:
    """Segments should have expected in/out variable identity."""
    h = create_solver()
    periods = np.array([1.0, 1.0])
    seg = case["factory"]("seg", 2, periods, h, spec=case["spec"])

    if case["expect_same"]:
        assert seg.power_in_st is seg.power_out_st
        assert seg.power_in_ts is seg.power_out_ts
    else:
        assert seg.power_in_st is not seg.power_out_st
        assert seg.power_in_ts is not seg.power_out_ts


def test_efficiency_reduces_output_power() -> None:
    """Output power should be input * efficiency."""
    h = create_solver()
    periods = np.array([1.0, 1.0])

    seg = EfficiencySegment(
        "eff",
        2,
        periods,
        h,
        spec={
            "segment_type": "efficiency",
            "efficiency_source_target": np.array([0.9, 0.9]),
            "efficiency_target_source": np.array([0.95, 0.95]),
        },
    )

    seg.constraints()

    h.addConstrs(seg.power_in_st == 10.0)
    h.addConstrs(seg.power_in_ts == 10.0)
    h.run()

    out_st = h.vals(seg.power_out_st)
    out_ts = h.vals(seg.power_out_ts)

    np.testing.assert_array_almost_equal(out_st, [9.0, 9.0])
    np.testing.assert_array_almost_equal(out_ts, [9.5, 9.5])


class PowerLimitCapCase(TypedDict):
    """Case describing a power limit constraint."""

    description: str
    spec: SegmentSpec
    attr: Literal["power_in_st", "power_in_ts"]
    expected: list[float]


POWER_LIMIT_CAP_CASES: Sequence[PowerLimitCapCase] = [
    {
        "description": "Caps source→target flow",
        "spec": {"segment_type": "power_limit", "max_power_source_target": np.array([5.0, 5.0])},
        "attr": "power_in_st",
        "expected": [5.0, 5.0],
    },
    {
        "description": "Caps target→source flow",
        "spec": {"segment_type": "power_limit", "max_power_target_source": np.array([3.0, 3.0])},
        "attr": "power_in_ts",
        "expected": [3.0, 3.0],
    },
]


@pytest.mark.parametrize("case", POWER_LIMIT_CAP_CASES, ids=lambda c: c["description"])
def test_power_limit_caps_flow(case: PowerLimitCapCase) -> None:
    """Power should be capped at configured max."""
    h = create_solver()
    periods = np.array([1.0, 1.0])

    seg = PowerLimitSegment("limit", 2, periods, h, spec=case["spec"])
    seg.constraints()

    flow = getattr(seg, case["attr"])
    h.minimize(-Highs.qsum(flow))
    h.run()

    values = h.vals(flow)
    np.testing.assert_array_almost_equal(values, case["expected"])


def test_power_limit_fixed_power_enforces_equality() -> None:
    """With fixed_power=True, power should equal max_power exactly."""
    h = create_solver()
    periods = np.array([1.0, 1.0])

    seg = PowerLimitSegment(
        "limit",
        2,
        periods,
        h,
        spec={"segment_type": "power_limit", "max_power_source_target": np.array([5.0, 5.0]), "fixed": True},
    )

    seg.constraints()
    h.run()

    in_st = h.vals(seg.power_in_st)
    np.testing.assert_array_almost_equal(in_st, [5.0, 5.0])


def test_power_limit_time_slice_constraint() -> None:
    """Normalized bidirectional flow should not exceed 1."""
    h = create_solver()
    periods = np.array([1.0])

    seg = PowerLimitSegment(
        "limit",
        1,
        periods,
        h,
        spec={
            "segment_type": "power_limit",
            "max_power_source_target": np.array([10.0]),
            "max_power_target_source": np.array([10.0]),
        },
    )

    seg.constraints()

    h.minimize(-Highs.qsum(seg.power_in_st) - Highs.qsum(seg.power_in_ts))
    h.run()

    in_st = h.vals(seg.power_in_st)
    in_ts = h.vals(seg.power_in_ts)

    normalized_sum = in_st[0] / 10.0 + in_ts[0] / 10.0
    assert normalized_sum <= 1.0 + 1e-6


def test_pricing_adds_cost() -> None:
    """Pricing segment should add cost to objective."""
    h = create_solver()
    periods = np.array([1.0, 0.5])

    seg = PricingSegment(
        "price",
        2,
        periods,
        h,
        spec={
            "segment_type": "pricing",
            "price_source_target": np.array([0.1, 0.1]),
            "price_target_source": np.array([0.2, 0.2]),
        },
    )

    h.addConstrs(seg.power_in_st == 10.0)
    h.addConstrs(seg.power_in_ts == 5.0)

    cost = seg.cost()
    assert cost is not None

    h.minimize(cost)
    h.run()

    expected_cost = (10 * 0.1 * 1.0) + (10 * 0.1 * 0.5) + (5 * 0.2 * 1.0) + (5 * 0.2 * 0.5)
    assert abs(h.getObjectiveValue() - expected_cost) < 0.001


class ConnectionSegmentCase(TypedDict):
    """Case describing a Connection segment creation."""

    description: str
    segments: dict[str, SegmentSpec]
    expected_type: type


CONNECTION_SEGMENT_CASES: Sequence[ConnectionSegmentCase] = [
    {
        "description": "Efficiency segment",
        "segments": {"efficiency": {"segment_type": "efficiency", "efficiency_source_target": np.array([0.90])}},
        "expected_type": EfficiencySegment,
    },
    {
        "description": "Power limit segment",
        "segments": {"power_limit": {"segment_type": "power_limit", "max_power_source_target": np.array([5.0])}},
        "expected_type": PowerLimitSegment,
    },
    {
        "description": "Pricing segment",
        "segments": {"pricing": {"segment_type": "pricing", "price_source_target": np.array([0.1])}},
        "expected_type": PricingSegment,
    },
]


@pytest.mark.parametrize("case", CONNECTION_SEGMENT_CASES, ids=lambda c: c["description"])
def test_connection_segment_creation(case: ConnectionSegmentCase) -> None:
    """Connection should create expected segment types."""
    h = create_solver()
    periods = [1.0]

    conn = Connection(
        name="conn",
        periods=periods,
        solver=h,
        source="src",
        target="tgt",
        segments=case["segments"],
    )

    segment_types = [type(s).__name__ for s in conn.segments.values()]
    assert case["expected_type"].__name__ in segment_types


def test_connection_with_no_modifiers_creates_passthrough() -> None:
    """Connection with no modifiers should create a passthrough segment."""
    h = create_solver()
    periods = [1.0, 1.0]

    conn = Connection(
        name="conn",
        periods=periods,
        solver=h,
        source="src",
        target="tgt",
    )

    assert len(conn._segments) == 1
    assert isinstance(conn["passthrough"], PassthroughSegment)


class ConnectionPowerLimitCase(TypedDict):
    """Case describing Connection power limit constraints."""

    description: str
    segments: dict[str, SegmentSpec]
    attr: Literal["power_source_target", "power_target_source"]
    expected: list[float]


CONNECTION_POWER_LIMIT_CASES: Sequence[ConnectionPowerLimitCase] = [
    {
        "description": "Source→target limit",
        "segments": {"power_limit": {"segment_type": "power_limit", "max_power_source_target": np.array([5.0, 5.0])}},
        "attr": "power_source_target",
        "expected": [5.0, 5.0],
    },
    {
        "description": "Target→source limit",
        "segments": {"power_limit": {"segment_type": "power_limit", "max_power_target_source": np.array([3.0, 3.0])}},
        "attr": "power_target_source",
        "expected": [3.0, 3.0],
    },
]


@pytest.mark.parametrize("case", CONNECTION_POWER_LIMIT_CASES, ids=lambda c: c["description"])
def test_connection_power_limit_caps_flow(case: ConnectionPowerLimitCase) -> None:
    """Connection power flow should be capped at max_power."""
    h = create_solver()
    periods = [1.0, 1.0]

    conn = Connection(
        name="conn",
        periods=periods,
        solver=h,
        source="src",
        target="tgt",
        segments=case["segments"],
    )

    conn.constraints()

    flow = getattr(conn, case["attr"])
    h.minimize(-Highs.qsum(flow))
    h.run()

    values = h.vals(flow)
    np.testing.assert_array_almost_equal(values, case["expected"])


def test_connection_efficiency_reduces_power() -> None:
    """Efficiency should reduce power into target."""
    h = create_solver()
    periods = [1.0]

    conn = Connection(
        name="conn",
        periods=periods,
        solver=h,
        source="src",
        target="tgt",
        segments={"efficiency": {"segment_type": "efficiency", "efficiency_source_target": np.array([0.90])}},
    )

    conn.constraints()
    h.addConstrs(conn.power_source_target == 10.0)
    h.run()

    into_target = h.vals(conn.power_into_target)
    assert abs(into_target[0] - 9.0) < 0.01


def test_connection_pricing_adds_cost() -> None:
    """Pricing should add cost to objective."""
    h = create_solver()
    periods = [1.0]

    conn = Connection(
        name="conn",
        periods=periods,
        solver=h,
        source="src",
        target="tgt",
        segments={"pricing": {"segment_type": "pricing", "price_source_target": np.array([0.1])}},
    )

    conn.constraints()
    h.addConstrs(conn.power_source_target == 10.0)

    cost_expr = conn.cost()
    assert cost_expr is not None

    h.minimize(cost_expr)
    h.run()

    assert abs(h.getObjectiveValue() - 1.0) < 0.001


def test_connection_segment_access_by_name_and_index() -> None:
    """Segments should be accessible by name and index."""
    h = create_solver()
    periods = [1.0, 1.0]

    conn = Connection(
        name="conn",
        periods=periods,
        solver=h,
        source="src",
        target="tgt",
        segments={
            "power_limit": {"segment_type": "power_limit", "max_power_source_target": np.array([5.0, 5.0])},
            "pricing": {"segment_type": "pricing", "price_source_target": np.array([0.1, 0.1])},
        },
    )

    assert isinstance(conn["power_limit"], PowerLimitSegment)
    assert isinstance(conn["pricing"], PricingSegment)

    assert isinstance(conn[0], PowerLimitSegment)
    assert isinstance(conn[1], PricingSegment)

    power_limit = conn["power_limit"]
    assert isinstance(power_limit, PowerLimitSegment)
    new_max_power = np.array([10.0, 10.0])
    power_limit.max_power_source_target = new_max_power
    np.testing.assert_array_equal(power_limit.max_power_source_target, new_max_power)

    pricing = conn["pricing"]
    assert isinstance(pricing, PricingSegment)
    new_price = np.array([0.2, 0.2])
    pricing.price_source_target = new_price
    np.testing.assert_array_equal(pricing.price_source_target, new_price)
