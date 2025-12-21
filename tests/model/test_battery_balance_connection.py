"""Model battery balance connection tests."""

from typing import Any

from highspy import Highs
import pytest

from custom_components.haeo.model.battery import Battery
from custom_components.haeo.model.battery_balance_connection import BatteryBalanceConnection
from custom_components.haeo.model.network import Network

from . import test_data
from .test_data.connection_types import ConnectionTestCase


def _create_balance_connection_with_batteries(
    solver: Highs,
    data: dict[str, Any],
    periods: list[float],
) -> tuple[BatteryBalanceConnection, Battery, Battery]:
    """Create a balance connection with mock batteries for testing.

    Args:
        solver: HiGHS solver instance
        data: Balance connection parameters
        periods: Period durations in hours

    Returns:
        Tuple of (balance_connection, upper_battery, lower_battery)

    """
    # Create mock batteries for testing
    upper_battery = Battery(
        name=data["upper"],
        periods=periods,
        solver=solver,
        capacity=10.0,  # Fixed capacity for upper section
        initial_charge=5.0,
    )

    lower_battery = Battery(
        name=data["lower"],
        periods=periods,
        solver=solver,
        capacity=data["capacity_lower"],  # Use the balance connection's capacity
        initial_charge=2.0,
    )

    # Create balance connection (remove solver from data since it's passed separately)
    balance_data = {k: v for k, v in data.items() if k != "solver"}
    balance_connection = BatteryBalanceConnection(
        **balance_data,
        periods=periods,
        solver=solver,
    )

    # Wire up references
    balance_connection.set_battery_references(upper_battery, lower_battery)

    return balance_connection, upper_battery, lower_battery


@pytest.mark.parametrize(
    "case",
    test_data.VALID_BALANCE_CONNECTION_CASES,
    ids=lambda case: case["description"].lower().replace(" ", "_"),
)
def test_balance_connection_upward_power(case: ConnectionTestCase, solver: Highs) -> None:
    """BatteryBalanceConnection should compute correct upward power from capacity shrinkage."""
    data = case["data"].copy()
    periods = data.pop("periods")
    data["solver"] = solver

    balance_connection, upper_battery, lower_battery = _create_balance_connection_with_batteries(solver, data, periods)

    # Build constraints for all elements
    upper_battery.build_constraints()
    lower_battery.build_constraints()
    balance_connection.build_constraints()

    # Run solver
    solver.run()

    # Get outputs and check upward power
    outputs = balance_connection.outputs()
    expected = case.get("expected_outputs", {})

    if "balance_power_up" in expected:
        actual_power_up = outputs["balance_power_up"]
        assert actual_power_up.values == pytest.approx(expected["balance_power_up"]["values"], rel=1e-9, abs=1e-9)


def test_balance_connection_network_integration(solver: Highs) -> None:
    """BatteryBalanceConnection should integrate with Network.add() correctly."""
    periods = [1.0, 1.0, 1.0]
    network = Network(name="test", periods=periods)

    # Add batteries first
    network.add("battery", "lower_section", capacity=[5.0, 4.0, 3.0, 3.0], initial_charge=3.0)
    network.add("battery", "upper_section", capacity=10.0, initial_charge=5.0)

    # Add balance connection
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=[5.0, 4.0, 3.0, 3.0],
    )

    # Verify the balance connection was registered correctly
    balance = network.elements["balance"]
    assert isinstance(balance, BatteryBalanceConnection)
    assert balance._upper_battery is not None
    assert balance._lower_battery is not None
    assert balance._upper_battery.name == "upper_section"
    assert balance._lower_battery.name == "lower_section"


def test_balance_connection_network_validation_missing_upper() -> None:
    """Network should raise error when balance connection upper battery is missing."""
    periods = [1.0, 1.0]
    network = Network(name="test", periods=periods)

    network.add("battery", "lower_section", capacity=5.0, initial_charge=2.0)

    with pytest.raises(TypeError, match="Upper element 'missing_battery' is not a battery"):
        network.add(
            "battery_balance_connection",
            "balance",
            upper="missing_battery",
            lower="lower_section",
            capacity_lower=[5.0, 5.0, 5.0],
        )


def test_balance_connection_network_validation_missing_lower() -> None:
    """Network should raise error when balance connection lower battery is missing."""
    periods = [1.0, 1.0]
    network = Network(name="test", periods=periods)

    network.add("battery", "upper_section", capacity=10.0, initial_charge=5.0)

    with pytest.raises(TypeError, match="Lower element 'missing_battery' is not a battery"):
        network.add(
            "battery_balance_connection",
            "balance",
            upper="upper_section",
            lower="missing_battery",
            capacity_lower=[5.0, 5.0, 5.0],
        )


def test_balance_connection_downward_transfer_minimum(solver: Highs) -> None:
    """Downward transfer should be at least equal to upward transfer."""
    periods = [1.0, 1.0]
    network = Network(name="test", periods=periods)

    # Lower section capacity shrinks from 5 to 4 kWh
    # This forces 1 kWh upward in first period (power_up = 1.0 kW)
    network.add("battery", "lower_section", capacity=[5.0, 4.0, 4.0], initial_charge=3.0)
    network.add("battery", "upper_section", capacity=10.0, initial_charge=5.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=[5.0, 4.0, 4.0],
    )

    # Run optimization
    network.optimize()

    # Get balance connection outputs
    balance = network.elements["balance"]
    outputs = balance.outputs()

    power_up = outputs["balance_power_up"].values
    power_down = outputs["balance_power_down"].values

    # Downward transfer should be >= upward transfer
    for i, (up, down) in enumerate(zip(power_up, power_down, strict=True)):
        assert down >= up - 1e-9, f"Period {i}: power_down ({down}) should be >= power_up ({up})"


def test_balance_connection_fills_lower_capacity() -> None:
    """Downward transfer should fill lower section's available capacity."""
    periods = [1.0, 1.0]
    network = Network(name="test", periods=periods)

    # Lower section has capacity 5 kWh, starts with 2 kWh
    # Upper section has plenty of energy to fill it
    network.add("battery", "lower_section", capacity=5.0, initial_charge=2.0)
    network.add("battery", "upper_section", capacity=10.0, initial_charge=8.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=5.0,
    )

    # Run optimization
    network.optimize()

    # Check that lower section is filled
    lower = network.elements["lower_section"]
    outputs = lower.outputs()

    # Final stored energy should be at capacity (5 kWh)
    stored_energy = outputs["battery_energy_stored"].values
    # Last value is at end of optimization horizon
    assert stored_energy[-1] == pytest.approx(5.0, rel=1e-6)
