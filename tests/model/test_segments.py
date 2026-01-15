"""Tests for connection segments and Connection class."""

from highspy import Highs
import numpy as np

from custom_components.haeo.model.elements.connection import Connection
from custom_components.haeo.model.elements.segments import (
    EfficiencySegment,
    PassthroughSegment,
    PowerLimitSegment,
    PricingSegment,
)


def create_solver() -> Highs:
    """Create a silent HiGHS solver."""
    h = Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("log_to_console", False)
    return h


class TestPassthroughSegment:
    """Tests for PassthroughSegment."""

    def test_passthrough_in_equals_out(self) -> None:
        """Power in should equal power out for passthrough segment (same variable)."""
        h = create_solver()
        periods = np.array([1.0, 1.0])

        seg = PassthroughSegment("pass", 2, periods, h)

        # In and out should be the same variable
        assert seg.power_in_st is seg.power_out_st
        assert seg.power_in_ts is seg.power_out_ts


class TestEfficiencySegment:
    """Tests for EfficiencySegment."""

    def test_efficiency_creates_separate_in_out_variables(self) -> None:
        """Efficiency segment should have separate input and output variables."""
        h = create_solver()
        periods = np.array([1.0, 1.0])

        seg = EfficiencySegment("eff", 2, periods, h, efficiency_st=np.array([0.9, 0.9]))

        # In and out should be different variables
        assert seg.power_in_st is not seg.power_out_st
        assert seg.power_in_ts is not seg.power_out_ts

    def test_efficiency_reduces_output_power(self) -> None:
        """Output power should be input * efficiency."""
        h = create_solver()
        periods = np.array([1.0, 1.0])

        seg = EfficiencySegment(
            "eff",
            2,
            periods,
            h,
            efficiency_st=np.array([0.9, 0.9]),
            efficiency_ts=np.array([0.95, 0.95]),
        )

        # Add efficiency constraints (calling constraints() adds them to solver)
        seg.constraints()

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

    def test_power_limit_in_equals_out(self) -> None:
        """Power in should equal power out for power limit segment (lossless)."""
        h = create_solver()
        periods = np.array([1.0, 1.0])

        seg = PowerLimitSegment("limit", 2, periods, h, max_power_st=np.array([5.0, 5.0]))

        # In and out should be the same variable
        assert seg.power_in_st is seg.power_out_st
        assert seg.power_in_ts is seg.power_out_ts

    def test_power_limit_caps_source_target_flow(self) -> None:
        """Power should be capped at max_power_st."""
        h = create_solver()
        periods = np.array([1.0, 1.0])

        seg = PowerLimitSegment(
            "limit",
            2,
            periods,
            h,
            max_power_st=np.array([5.0, 5.0]),
            # Only set one direction to avoid time-slice constraint
        )

        # Add power limit constraints (calling constraints() adds them to solver)
        seg.constraints()

        # Try to maximize power flow
        h.minimize(-Highs.qsum(seg.power_in_st))
        h.run()

        in_st = h.vals(seg.power_in_st)
        np.testing.assert_array_almost_equal(in_st, [5.0, 5.0])

    def test_power_limit_caps_target_source_flow(self) -> None:
        """Power should be capped at max_power_ts."""
        h = create_solver()
        periods = np.array([1.0, 1.0])

        seg = PowerLimitSegment(
            "limit",
            2,
            periods,
            h,
            max_power_ts=np.array([3.0, 3.0]),
            # Only set one direction to avoid time-slice constraint
        )

        # Add power limit constraints (calling constraints() adds them to solver)
        seg.constraints()

        # Try to maximize power flow
        h.minimize(-Highs.qsum(seg.power_in_ts))
        h.run()

        in_ts = h.vals(seg.power_in_ts)
        np.testing.assert_array_almost_equal(in_ts, [3.0, 3.0])

    def test_fixed_power_enforces_equality(self) -> None:
        """With fixed_power=True, power should equal max_power exactly."""
        h = create_solver()
        periods = np.array([1.0, 1.0])

        seg = PowerLimitSegment(
            "limit",
            2,
            periods,
            h,
            max_power_st=np.array([5.0, 5.0]),
            fixed=True,
        )

        # Add power limit constraints (calling constraints() adds them to solver)
        seg.constraints()

        h.run()

        in_st = h.vals(seg.power_in_st)
        np.testing.assert_array_almost_equal(in_st, [5.0, 5.0])

    def test_time_slice_constraint(self) -> None:
        """Normalized bidirectional flow should not exceed 1."""
        h = create_solver()
        periods = np.array([1.0])

        seg = PowerLimitSegment(
            "limit",
            1,
            periods,
            h,
            max_power_st=np.array([10.0]),
            max_power_ts=np.array([10.0]),
        )

        # Add constraints (calling constraints() adds them to solver)
        seg.constraints()

        # Try to maximize both directions
        h.minimize(-Highs.qsum(seg.power_in_st) - Highs.qsum(seg.power_in_ts))
        h.run()

        in_st = h.vals(seg.power_in_st)
        in_ts = h.vals(seg.power_in_ts)

        # Normalized sum should be <= 1
        normalized_sum = in_st[0] / 10.0 + in_ts[0] / 10.0
        assert normalized_sum <= 1.0 + 1e-6


class TestPricingSegment:
    """Tests for PricingSegment."""

    def test_pricing_in_equals_out(self) -> None:
        """Power in should equal power out for pricing segment (lossless)."""
        h = create_solver()
        periods = np.array([1.0, 1.0])

        seg = PricingSegment("price", 2, periods, h, price_st=np.array([0.1, 0.1]))

        # In and out should be the same variable
        assert seg.power_in_st is seg.power_out_st
        assert seg.power_in_ts is seg.power_out_ts

    def test_pricing_adds_cost(self) -> None:
        """Pricing segment should add cost to objective."""
        h = create_solver()
        periods = np.array([1.0, 0.5])  # Different period lengths

        seg = PricingSegment(
            "price",
            2,
            periods,
            h,
            price_st=np.array([0.1, 0.1]),
            price_ts=np.array([0.2, 0.2]),
        )

        # Fix power flows
        h.addConstrs(seg.power_in_st == 10.0)
        h.addConstrs(seg.power_in_ts == 5.0)

        cost = seg.cost()
        assert cost is not None

        h.minimize(cost)
        h.run()

        # Expected cost: (10 * 0.1 * 1.0) + (10 * 0.1 * 0.5) + (5 * 0.2 * 1.0) + (5 * 0.2 * 0.5)
        # = 1.0 + 0.5 + 1.0 + 0.5 = 3.0
        expected_cost = (10 * 0.1 * 1.0) + (10 * 0.1 * 0.5) + (5 * 0.2 * 1.0) + (5 * 0.2 * 0.5)
        assert abs(h.getObjectiveValue() - expected_cost) < 0.001


class TestConnection:
    """Tests for Connection."""

    def test_connection_with_no_modifiers_creates_passthrough(self) -> None:
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

        # Should have exactly one segment (passthrough)
        assert len(conn._segments) == 1
        assert isinstance(conn["passthrough"], PassthroughSegment)

    def test_connection_with_efficiency(self) -> None:
        """Connection with efficiency should create an efficiency segment."""
        h = create_solver()
        periods = [1.0]

        conn = Connection(
            name="conn",
            periods=periods,
            solver=h,
            source="src",
            target="tgt",
            segments=[{"segment_type": "efficiency", "efficiency_st": np.array([0.90])}],
        )

        # Should have efficiency segment
        segment_types = [type(s).__name__ for s in conn.segments.values()]
        assert "EfficiencySegment" in segment_types

    def test_connection_with_power_limit(self) -> None:
        """Connection with max_power should create a power limit segment."""
        h = create_solver()
        periods = [1.0]

        conn = Connection(
            name="conn",
            periods=periods,
            solver=h,
            source="src",
            target="tgt",
            segments=[{"segment_type": "power_limit", "max_power_st": np.array([5.0])}],
        )

        # Should have power limit segment
        segment_types = [type(s).__name__ for s in conn.segments.values()]
        assert "PowerLimitSegment" in segment_types

    def test_connection_with_pricing(self) -> None:
        """Connection with price should create a pricing segment."""
        h = create_solver()
        periods = [1.0]

        conn = Connection(
            name="conn",
            periods=periods,
            solver=h,
            source="src",
            target="tgt",
            segments=[{"segment_type": "pricing", "price_st": np.array([0.1])}],
        )

        # Should have pricing segment
        segment_types = [type(s).__name__ for s in conn.segments.values()]
        assert "PricingSegment" in segment_types

    def test_connection_power_limit_caps_source_target_flow(self) -> None:
        """Source→target power should be capped at max_power_st."""
        h = create_solver()
        periods = [1.0, 1.0]

        conn = Connection(
            name="conn",
            periods=periods,
            solver=h,
            source="src",
            target="tgt",
            segments=[{"segment_type": "power_limit", "max_power_st": np.array([5.0, 5.0])}],
        )

        # Add all constraints (calling constraints() adds them to solver)
        conn.constraints()

        # Try to maximize power flow
        h.minimize(-Highs.qsum(conn.power_source_target))
        h.run()

        st = h.vals(conn.power_source_target)
        np.testing.assert_array_almost_equal(st, [5.0, 5.0])

    def test_connection_power_limit_caps_target_source_flow(self) -> None:
        """Target→source power should be capped at max_power_ts."""
        h = create_solver()
        periods = [1.0, 1.0]

        conn = Connection(
            name="conn",
            periods=periods,
            solver=h,
            source="src",
            target="tgt",
            segments=[{"segment_type": "power_limit", "max_power_ts": np.array([3.0, 3.0])}],
        )

        # Add all constraints (calling constraints() adds them to solver)
        conn.constraints()

        # Try to maximize power flow
        h.minimize(-Highs.qsum(conn.power_target_source))
        h.run()

        ts = h.vals(conn.power_target_source)
        np.testing.assert_array_almost_equal(ts, [3.0, 3.0])

    def test_connection_efficiency_reduces_power(self) -> None:
        """Efficiency should reduce power into target."""
        h = create_solver()
        periods = [1.0]

        conn = Connection(
            name="conn",
            periods=periods,
            solver=h,
            source="src",
            target="tgt",
            segments=[{"segment_type": "efficiency", "efficiency_st": np.array([0.90])}],
        )

        # Add all constraints (calling constraints() adds them to solver)
        conn.constraints()

        # Fix input power at 10 kW
        h.addConstrs(conn.power_source_target == 10.0)
        h.run()

        # Power into target should be 10 * 0.9 = 9.0 kW
        into_target = h.vals(conn.power_into_target)
        assert abs(into_target[0] - 9.0) < 0.01

    def test_connection_pricing_adds_cost(self) -> None:
        """Pricing should add cost to objective."""
        h = create_solver()
        periods = [1.0]

        conn = Connection(
            name="conn",
            periods=periods,
            solver=h,
            source="src",
            target="tgt",
            segments=[{"segment_type": "pricing", "price_st": np.array([0.1])}],
        )

        # Add all constraints (calling constraints() adds them to solver)
        conn.constraints()

        # Fix power at 10 kW
        h.addConstrs(conn.power_source_target == 10.0)

        # Get cost from connection
        cost_expr = conn.cost()
        assert cost_expr is not None

        h.minimize(cost_expr)
        h.run()

        # Expected cost: 10 kW * 0.1 $/kWh * 1.0 hours = 1.0
        assert abs(h.getObjectiveValue() - 1.0) < 0.001

    def test_connection_segment_access_by_name_and_index(self) -> None:
        """Segments should be accessible by name and index."""
        h = create_solver()
        periods = [1.0, 1.0]

        conn = Connection(
            name="conn",
            periods=periods,
            solver=h,
            source="src",
            target="tgt",
            segments=[
                {"segment_type": "power_limit", "max_power_st": np.array([5.0, 5.0])},
                {"segment_type": "pricing", "price_st": np.array([0.1, 0.1])},
            ],
        )

        # Access by name
        assert isinstance(conn["power_limit"], PowerLimitSegment)
        assert isinstance(conn["pricing"], PricingSegment)

        # Access by index
        assert isinstance(conn[0], PowerLimitSegment)
        assert isinstance(conn[1], PricingSegment)

        # Update via segment attribute access
        power_limit = conn["power_limit"]
        assert isinstance(power_limit, PowerLimitSegment)
        new_max_power = np.array([10.0, 10.0])
        power_limit.max_power_st = new_max_power
        np.testing.assert_array_equal(power_limit.max_power_st, new_max_power)

        pricing = conn["pricing"]
        assert isinstance(pricing, PricingSegment)
        new_price = np.array([0.2, 0.2])
        pricing.price_st = new_price
        np.testing.assert_array_equal(pricing.price_st, new_price)
