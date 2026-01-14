"""Tests for composed connection segments."""

import pytest
from highspy import Highs
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.model.elements.composite_connection import CompositeConnection
from custom_components.haeo.model.elements.segments import (
    EfficiencySegment,
    PassthroughSegment,
    PowerLimitSegment,
    PricingSegment,
    TimeSliceSegment,
)


def create_solver() -> Highs:
    """Create a silent HiGHS solver."""
    h = Highs()
    h.silent()
    return h


class TestPassthroughSegment:
    """Tests for PassthroughSegment."""

    def test_passthrough_forwards_power_unchanged(self) -> None:
        """Power out should equal power in for passthrough segment."""
        h = create_solver()
        periods = np.array([1.0, 1.0])

        seg = PassthroughSegment("pass", periods, h)
        seg.add_constraints()

        # Fix input and maximize output (should be equal)
        h.addConstrs(seg.power_in_st == 5.0)
        h.run()

        in_vals = h.vals(seg.power_in_st)
        out_vals = h.vals(seg.power_out_st)

        np.testing.assert_array_almost_equal(in_vals, out_vals)


class TestEfficiencySegment:
    """Tests for EfficiencySegment."""

    def test_efficiency_reduces_output_power(self) -> None:
        """Output power should be input * efficiency."""
        h = create_solver()
        periods = np.array([1.0, 1.0])

        seg = EfficiencySegment("eff", periods, h, efficiency_st=0.9, efficiency_ts=0.95)
        seg.add_constraints()

        # Fix input power to 10 kW
        h.addConstrs(seg.power_in_st == 10.0)
        h.addConstrs(seg.power_in_ts == 10.0)
        h.run()

        out_st = h.vals(seg.power_out_st)
        out_ts = h.vals(seg.power_out_ts)

        np.testing.assert_array_almost_equal(out_st, [9.0, 9.0])  # 10 * 0.9
        np.testing.assert_array_almost_equal(out_ts, [9.5, 9.5])  # 10 * 0.95


class TestPowerLimitSegment:
    """Tests for PowerLimitSegment."""

    def test_power_limit_caps_flow(self) -> None:
        """Power should be capped at max_power."""
        h = create_solver()
        periods = np.array([1.0, 1.0])

        seg = PowerLimitSegment("limit", periods, h, max_power_st=5.0, max_power_ts=3.0)
        seg.add_constraints()

        # Try to maximize power flow
        h.minimize(-Highs.qsum(seg.power_in_st) - Highs.qsum(seg.power_in_ts))
        h.run()

        in_st = h.vals(seg.power_in_st)
        in_ts = h.vals(seg.power_in_ts)

        np.testing.assert_array_almost_equal(in_st, [5.0, 5.0])
        np.testing.assert_array_almost_equal(in_ts, [3.0, 3.0])

    def test_fixed_power_enforces_equality(self) -> None:
        """With fixed_power=True, power should equal max_power exactly."""
        h = create_solver()
        periods = np.array([1.0, 1.0])

        seg = PowerLimitSegment("limit", periods, h, max_power_st=5.0, fixed_power=True)
        seg.add_constraints()

        h.run()

        in_st = h.vals(seg.power_in_st)
        np.testing.assert_array_almost_equal(in_st, [5.0, 5.0])


class TestPricingSegment:
    """Tests for PricingSegment."""

    def test_pricing_adds_cost(self) -> None:
        """Pricing segment should add cost to objective."""
        h = create_solver()
        periods = np.array([1.0, 0.5])  # Different period lengths

        seg = PricingSegment("price", periods, h, price_st=0.1, price_ts=0.2)
        seg.add_constraints()

        # Fix power flows
        h.addConstrs(seg.power_in_st == 10.0)
        h.addConstrs(seg.power_in_ts == 5.0)

        cost = seg.costs()
        assert cost is not None

        h.minimize(cost)
        h.run()

        # Expected cost: (10 * 0.1 * 1.0) + (10 * 0.1 * 0.5) + (5 * 0.2 * 1.0) + (5 * 0.2 * 0.5)
        # = 1.0 + 0.5 + 1.0 + 0.5 = 3.0
        expected_cost = (10 * 0.1 * 1.0) + (10 * 0.1 * 0.5) + (5 * 0.2 * 1.0) + (5 * 0.2 * 0.5)
        assert abs(h.getInfo().objective_function_value - expected_cost) < 0.001


class TestTimeSliceSegment:
    """Tests for TimeSliceSegment."""

    def test_time_slice_prevents_full_bidirectional(self) -> None:
        """Normalized bidirectional flow should not exceed 1."""
        h = create_solver()
        periods = np.array([1.0])

        seg = TimeSliceSegment("ts", periods, h, capacity_st=10.0, capacity_ts=10.0)
        seg.add_constraints()

        # Try to maximize both directions
        h.minimize(-Highs.qsum(seg.power_in_st) - Highs.qsum(seg.power_in_ts))
        h.run()

        in_st = h.vals(seg.power_in_st)
        in_ts = h.vals(seg.power_in_ts)

        # Normalized sum should be <= 1
        normalized_sum = in_st[0] / 10.0 + in_ts[0] / 10.0
        assert normalized_sum <= 1.0 + 1e-6


class TestCompositeConnection:
    """Tests for CompositeConnection."""

    def test_single_passthrough_segment(self) -> None:
        """Single passthrough segment should work like lossless connection."""
        h = create_solver()
        periods = np.array([1.0, 1.0])

        seg = PassthroughSegment("pass", periods, h)
        conn = CompositeConnection(
            name="conn",
            periods=periods,
            solver=h,
            source="src",
            target="tgt",
            segments=[seg],
        )

        conn.constraints()

        # Add upper bounds and maximize
        h.addConstrs(conn.power_source_target <= 5.0)
        h.minimize(-Highs.qsum(conn.power_source_target))
        h.run()

        vals = h.vals(conn.power_source_target)
        np.testing.assert_array_almost_equal(vals, [5.0, 5.0])

    def test_efficiency_then_limit_chain(self) -> None:
        """Chain efficiency before limit - power reduced before limiting."""
        h = create_solver()
        periods = np.array([1.0])

        # 90% efficiency followed by 5 kW limit
        eff = EfficiencySegment("eff", periods, h, efficiency_st=0.9, efficiency_ts=0.9)
        limit = PowerLimitSegment("limit", periods, h, max_power_st=5.0, max_power_ts=5.0)

        conn = CompositeConnection(
            name="conn",
            periods=periods,
            solver=h,
            source="src",
            target="tgt",
            segments=[eff, limit],
        )

        conn.constraints()

        # Maximize power through
        h.minimize(-Highs.qsum(conn.power_source_target))
        h.run()

        # Input power should be 5.0 / 0.9 ≈ 5.55 to get 5.0 out of efficiency into limit
        in_power = h.vals(conn.power_source_target)
        # After efficiency: 5.55 * 0.9 = 5.0 which hits the limit
        assert in_power[0] > 5.0  # More than limit because efficiency reduces
        assert abs(in_power[0] - 5.0 / 0.9) < 0.01

    def test_composite_power_into_endpoints(self) -> None:
        """power_into_source/target should reflect full chain effects."""
        h = create_solver()
        periods = np.array([1.0])

        # 90% efficiency
        eff = EfficiencySegment("eff", periods, h, efficiency_st=0.9, efficiency_ts=0.9)

        conn = CompositeConnection(
            name="conn",
            periods=periods,
            solver=h,
            source="src",
            target="tgt",
            segments=[eff],
        )

        conn.constraints()

        # Fix source→target power at 10 kW
        h.addConstrs(conn.power_source_target == 10.0)
        h.run()

        # Power into source: -10 (power leaving)
        # Power into target: 9 (10 * 0.9, power arriving after efficiency)
        into_source = h.vals(conn.power_into_source)
        into_target = h.vals(conn.power_into_target)

        assert abs(into_source[0] - (-10.0)) < 0.01
        assert abs(into_target[0] - 9.0) < 0.01

    def test_composite_with_pricing(self) -> None:
        """Pricing segment costs should be included in composite cost."""
        h = create_solver()
        periods = np.array([1.0])

        pricing = PricingSegment("price", periods, h, price_st=0.1)

        conn = CompositeConnection(
            name="conn",
            periods=periods,
            solver=h,
            source="src",
            target="tgt",
            segments=[pricing],
        )

        conn.constraints()

        # Fix power at 10 kW
        h.addConstrs(conn.power_source_target == 10.0)

        # Get cost from composite
        cost_expr = conn.cost()
        assert cost_expr is not None

        h.minimize(cost_expr)
        h.run()

        # Expected: 10 * 0.1 * 1.0 = 1.0
        assert abs(h.getInfo().objective_function_value - 1.0) < 0.001

    def test_requires_at_least_one_segment(self) -> None:
        """CompositeConnection should require at least one segment."""
        h = create_solver()
        periods = np.array([1.0])

        with pytest.raises(ValueError, match="requires at least one segment"):
            CompositeConnection(
                name="conn",
                periods=periods,
                solver=h,
                source="src",
                target="tgt",
                segments=[],
            )
