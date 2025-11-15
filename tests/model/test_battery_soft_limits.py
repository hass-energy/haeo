"""Test battery soft limits (overcharge/undercharge) functionality."""

from pulp import LpVariable
import pytest

from custom_components.haeo.model.battery import Battery


def test_battery_with_overcharge_only() -> None:
    """Test battery with overcharge soft limit and cost."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=3,
        capacity=10.0,
        initial_charge_percentage=50.0,
        min_charge_percentage=10.0,
        max_charge_percentage=90.0,
        overcharge_percentage=80.0,
        overcharge_cost=5.0,
    )

    # Verify slack variables created
    assert battery.overcharge_slack is not None
    assert len(battery.overcharge_slack) == 2
    assert battery.undercharge_slack is None

    # Verify slack bounds (10% of 10kWh capacity = 1kWh max slack)
    for slack_var in battery.overcharge_slack:
        assert isinstance(slack_var, LpVariable)
        assert slack_var.lowBound == 0
        assert slack_var.upBound == 1.0

    # Verify cost values
    assert battery.overcharge_cost_values == [5.0, 5.0, 5.0]

    # Verify constraints include soft limit
    constraints = battery.constraints()
    assert len(constraints) > 0


def test_battery_with_undercharge_only() -> None:
    """Test battery with undercharge soft limit and cost."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=3,
        capacity=10.0,
        initial_charge_percentage=50.0,
        min_charge_percentage=10.0,
        max_charge_percentage=90.0,
        undercharge_percentage=20.0,
        undercharge_cost=3.0,
    )

    # Verify slack variables created
    assert battery.undercharge_slack is not None
    assert len(battery.undercharge_slack) == 2
    assert battery.overcharge_slack is None

    # Verify slack bounds (10% of 10kWh capacity = 1kWh max slack)
    for slack_var in battery.undercharge_slack:
        assert isinstance(slack_var, LpVariable)
        assert slack_var.lowBound == 0
        assert slack_var.upBound == 1.0

    # Verify cost values
    assert battery.undercharge_cost_values == [3.0, 3.0, 3.0]


def test_battery_with_both_soft_limits() -> None:
    """Test battery with both overcharge and undercharge soft limits."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=3,
        capacity=10.0,
        initial_charge_percentage=50.0,
        min_charge_percentage=5.0,
        max_charge_percentage=95.0,
        undercharge_percentage=10.0,
        overcharge_percentage=90.0,
        undercharge_cost=2.0,
        overcharge_cost=4.0,
    )

    # Verify both slack variables created
    assert battery.overcharge_slack is not None
    assert battery.undercharge_slack is not None
    assert len(battery.overcharge_slack) == 2
    assert len(battery.undercharge_slack) == 2

    # Verify slack bounds
    for slack_var in battery.overcharge_slack:
        assert slack_var.upBound == 0.5  # 5% of 10kWh

    for slack_var in battery.undercharge_slack:
        assert slack_var.upBound == 0.5  # 5% of 10kWh

    # Verify cost values
    assert battery.overcharge_cost_values == [4.0, 4.0, 4.0]
    assert battery.undercharge_cost_values == [2.0, 2.0, 2.0]


def test_battery_without_soft_limits() -> None:
    """Test battery without soft limits (existing behavior)."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=3,
        capacity=10.0,
        initial_charge_percentage=50.0,
    )

    # Verify no slack variables created
    assert battery.overcharge_slack is None
    assert battery.undercharge_slack is None
    assert battery.overcharge_cost_values is None
    assert battery.undercharge_cost_values is None


def test_battery_with_time_varying_costs() -> None:
    """Test battery with time-varying over/undercharge costs."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=3,
        capacity=10.0,
        initial_charge_percentage=50.0,
        min_charge_percentage=10.0,
        max_charge_percentage=90.0,
        undercharge_percentage=20.0,
        overcharge_percentage=80.0,
        undercharge_cost=[1.0, 2.0, 3.0],
        overcharge_cost=[4.0, 5.0, 6.0],
    )

    # Verify cost values broadcasted correctly
    assert battery.undercharge_cost_values == [1.0, 2.0, 3.0]
    assert battery.overcharge_cost_values == [4.0, 5.0, 6.0]


def test_battery_soft_limit_only_without_cost() -> None:
    """Test battery with soft limit but no cost (should not create slack)."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=3,
        capacity=10.0,
        initial_charge_percentage=50.0,
        overcharge_percentage=80.0,
    )

    # No slack should be created without cost
    assert battery.overcharge_slack is None
    assert battery.undercharge_slack is None


def test_battery_cost_only_without_soft_limit() -> None:
    """Test battery with cost but no soft limit (should not create slack)."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=3,
        capacity=10.0,
        initial_charge_percentage=50.0,
        overcharge_cost=5.0,
    )

    # No slack should be created without soft limit
    assert battery.overcharge_slack is None
    assert battery.undercharge_slack is None


def test_battery_soft_limits_constraints() -> None:
    """Test that soft limit constraints are properly added."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=3,
        capacity=10.0,
        initial_charge_percentage=50.0,
        min_charge_percentage=10.0,
        max_charge_percentage=90.0,
        undercharge_percentage=20.0,
        overcharge_percentage=80.0,
        undercharge_cost=2.0,
        overcharge_cost=4.0,
    )

    constraints = battery.constraints()

    # Should have energy balance constraints (n_periods - 1 = 2)
    # Plus soft limit constraints (2 for soft_max, 2 for soft_min)
    # Total: 2 + 2 + 2 = 6 constraints
    assert len(constraints) >= 6


def test_battery_soft_limits_cost() -> None:
    """Test that soft limit costs are properly added."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=3,
        capacity=10.0,
        initial_charge_percentage=50.0,
        min_charge_percentage=10.0,
        max_charge_percentage=90.0,
        undercharge_percentage=20.0,
        overcharge_percentage=80.0,
        undercharge_cost=2.0,
        overcharge_cost=4.0,
    )

    # Cost should be calculable (even with zero slack variable values)
    cost = battery.cost()
    assert cost is not None


def test_battery_with_varying_capacity() -> None:
    """Test battery with time-varying capacity and soft limits."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=3,
        capacity=[10.0, 12.0, 15.0],
        initial_charge_percentage=50.0,
        min_charge_percentage=10.0,
        max_charge_percentage=90.0,
        undercharge_percentage=20.0,
        overcharge_percentage=80.0,
        undercharge_cost=2.0,
        overcharge_cost=4.0,
    )

    # Slack bounds should scale with capacity
    assert battery.overcharge_slack is not None
    assert battery.undercharge_slack is not None

    # At t=1: capacity=12.0, slack = (90-80)*12/100 = 1.2
    # At t=2: capacity=15.0, slack = (90-80)*15/100 = 1.5
    assert battery.overcharge_slack[0].upBound == pytest.approx(1.2)
    assert battery.overcharge_slack[1].upBound == pytest.approx(1.5)

    # At t=1: capacity=12.0, slack = (20-10)*12/100 = 1.2
    # At t=2: capacity=15.0, slack = (20-10)*15/100 = 1.5
    assert battery.undercharge_slack[0].upBound == pytest.approx(1.2)
    assert battery.undercharge_slack[1].upBound == pytest.approx(1.5)
