"""Integration tests for Network optimization scenarios."""

from numbers import Real
from typing import cast

from pulp import LpVariable, value
import pytest

from custom_components.haeo.elements import (
    ELEMENT_TYPE_BATTERY,
    ELEMENT_TYPE_CONNECTION,
    ELEMENT_TYPE_GRID,
    ELEMENT_TYPE_LOAD,
    ELEMENT_TYPE_NODE,
    ELEMENT_TYPE_PHOTOVOLTAICS,
)
from custom_components.haeo.model import Network
from custom_components.haeo.model.battery import Battery
from custom_components.haeo.model.photovoltaics import Photovoltaics

# Test constants
SECONDS_PER_HOUR = 3600
MAX_POWER_LIMIT = 3000
REVERSE_POWER_LIMIT = 2000


def safe_value(var: LpVariable | float | None) -> float:
    """Return a numeric value for PuLP variables or raw numbers."""
    if var is None:
        return 0.0
    if isinstance(var, Real):
        return float(var)
    return float(value(var))  # type: ignore[no-untyped-call]


def test_simple_optimization() -> None:
    """Test a simple optimization scenario."""
    network = Network(
        name="test_network",
        period=SECONDS_PER_HOUR,
        n_periods=3,
    )

    # Add a simple grid and load
    network.add(
        ELEMENT_TYPE_GRID,
        "grid",
        import_limit=10000,
        export_limit=5000,
        import_price=[0.1, 0.2, 0.15],
        export_price=[0.05, 0.08, 0.06],
    )
    network.add(ELEMENT_TYPE_LOAD, "load", forecast=[1000, 1500, 2000])
    network.add(ELEMENT_TYPE_NODE, "net")

    # Connect them: grid -> net <- load
    network.add(ELEMENT_TYPE_CONNECTION, "grid_to_net", source="grid", target="net")
    network.add(ELEMENT_TYPE_CONNECTION, "net_to_load", source="net", target="load")

    # Run optimization
    cost = network.optimize()

    assert isinstance(cost, (int, float))


def test_battery_solar_grid_storage_cycle() -> None:
    """Test a scenario with grid, battery, and solar with storage and discharge cycles.

    Uses square wave patterns to force energy storage during high generation
    and discharge during high demand periods.
    """
    network = Network(
        name="storage_cycle_test",
        period=SECONDS_PER_HOUR,  # 1 hour periods
        n_periods=8,  # 8 hour test
    )

    # Solar generation with square wave pattern: high generation for 4 hours, then none
    solar_forecast = [5000, 5000, 5000, 5000, 0, 0, 0, 0]

    # Load demand with inverse square wave: low for 4 hours, then high
    load_forecast = [1000, 1000, 1000, 1000, 4000, 4000, 4000, 4000]

    # Grid pricing: cheap during high solar, expensive during low solar
    import_prices = [0.05, 0.05, 0.05, 0.05, 0.20, 0.20, 0.20, 0.20]
    export_prices = [0.03, 0.03, 0.03, 0.03, 0.15, 0.15, 0.15, 0.15]

    # Add entities
    network.add(
        ELEMENT_TYPE_PHOTOVOLTAICS,
        "solar",
        forecast=solar_forecast,
        curtailment=True,
        price_production=[0] * 8,
    )  # Solar has no fuel cost

    network.add(ELEMENT_TYPE_LOAD, "load", forecast=load_forecast)

    network.add(
        ELEMENT_TYPE_BATTERY,
        "battery",
        capacity=10000,  # 10 kWh
        initial_charge_percentage=50,
        min_charge_percentage=20,
        max_charge_percentage=90,
        max_charge_power=MAX_POWER_LIMIT,
        max_discharge_power=MAX_POWER_LIMIT,
        efficiency=0.95,
    )

    network.add(
        ELEMENT_TYPE_GRID,
        "grid",
        import_limit=10000,
        export_limit=10000,
        import_price=import_prices,
        export_price=export_prices,
    )

    network.add(ELEMENT_TYPE_NODE, "net")

    # Connect everything through the net
    network.add(ELEMENT_TYPE_CONNECTION, "solar_to_net", source="solar", target="net")
    network.add(ELEMENT_TYPE_CONNECTION, "battery_to_net", source="battery", target="net")
    network.add(ELEMENT_TYPE_CONNECTION, "grid_to_net", source="grid", target="net")
    network.add(ELEMENT_TYPE_CONNECTION, "net_to_load", source="net", target="load")

    # Run optimization
    cost = network.optimize()

    # Verify the solution makes economic sense
    assert isinstance(cost, (int, float))
    assert cost > 0  # Should have some cost


def test_optimization_failure() -> None:
    """Test optimization failure handling."""
    network = Network(
        name="test_network",
        period=SECONDS_PER_HOUR,
        n_periods=3,
    )

    # Create an infeasible optimization problem by adding conflicting constraints
    # Add a battery with impossible constraints
    network.add(
        ELEMENT_TYPE_BATTERY,
        "battery",
        capacity=1000,
        initial_charge_percentage=50,
        min_charge_percentage=90,  # Impossible - starting charge is below minimum
        max_charge_power=0,  # Can't charge
        max_discharge_power=0,  # Can't discharge
    )

    # This should result in an infeasible optimization problem
    with pytest.raises(ValueError, match="Optimization failed with status"):
        network.optimize()


def test_connection_power_balance_with_negative_flow() -> None:
    """Test that power balance works correctly with negative power flows."""
    network = Network(
        name="test_network",
        period=SECONDS_PER_HOUR,
        n_periods=3,
    )

    # Add entities
    network.add(ELEMENT_TYPE_BATTERY, "battery1", capacity=10000, initial_charge_percentage=50)
    network.add(
        ELEMENT_TYPE_GRID,
        "grid1",
        import_limit=10000,
        export_limit=5000,
        import_price=[0.1, 0.2, 0.15],
        export_price=[0.05, 0.08, 0.06],
    )

    # Create bidirectional connection
    network.add(
        ELEMENT_TYPE_CONNECTION,
        "battery_grid_bidirectional",
        source="battery1",
        target="grid1",
        min_power=-REVERSE_POWER_LIMIT,  # Allow reverse flow
        max_power=MAX_POWER_LIMIT,  # Allow forward flow
    )

    # Validate the network (should pass)
    network.validate()

    # Run optimization
    cost = network.optimize()

    # Should complete without errors
    assert isinstance(cost, (int, float))

    # Access optimization results
    battery = cast("Battery", network.elements["battery1"])

    # Check that power variables exist and have values
    assert battery.power_consumption is not None
    for power_var in battery.power_consumption:
        assert isinstance(safe_value(power_var), (int, float))


def test_solar_curtailment_negative_pricing() -> None:
    """Test solar curtailment during negative export pricing periods.

    This scenario tests the system's ability to curtail solar generation
    when export prices are negative (grid operator pays to take power).
    """
    network = Network(
        name="curtailment_test",
        period=SECONDS_PER_HOUR,
        n_periods=6,
    )

    # High solar generation throughout the test period
    solar_forecast = [6000, 6000, 6000, 6000, 6000, 6000]

    # Low load - creates excess generation that needs to be exported
    load_forecast = [1000, 1000, 1000, 1000, 1000, 1000]

    # Grid pricing with negative export prices in the middle periods
    import_prices = [0.10, 0.10, 0.10, 0.10, 0.10, 0.10]
    export_prices = [0.05, 0.05, -0.02, -0.02, 0.05, 0.05]  # Negative pricing in periods 2-3

    # Add entities
    network.add(
        ELEMENT_TYPE_PHOTOVOLTAICS,
        "solar",
        forecast=solar_forecast,
        curtailment=True,  # Allow curtailment
        price_production=[0] * 6,
    )  # No fuel cost for solar

    network.add(ELEMENT_TYPE_LOAD, "load", forecast=load_forecast)

    network.add(
        ELEMENT_TYPE_GRID,
        "grid",
        import_limit=10000,
        export_limit=10000,
        import_price=import_prices,
        export_price=export_prices,
    )

    network.add(ELEMENT_TYPE_NODE, "net")

    # Connect entities
    network.add(ELEMENT_TYPE_CONNECTION, "solar_to_net", source="solar", target="net")
    network.add(ELEMENT_TYPE_CONNECTION, "grid_to_net", source="grid", target="net")
    network.add(ELEMENT_TYPE_CONNECTION, "net_to_load", source="net", target="load")

    # Run optimization
    cost = network.optimize()

    # Verify solution
    assert isinstance(cost, (int, float))

    # Access optimization results directly from elements
    solar = cast("Photovoltaics", network.elements["solar"])

    assert solar.power_production is not None
    solar_production = [safe_value(power) for power in solar.power_production]

    # During negative pricing periods (indices 2-3), solar should be curtailed
    normal_periods = [0, 1, 4, 5]  # Positive export pricing
    negative_periods = [2, 3]  # Negative export pricing

    # Solar should produce less during negative pricing periods
    avg_solar_normal = sum(solar_production[i] for i in normal_periods) / len(normal_periods)
    avg_solar_negative = sum(solar_production[i] for i in negative_periods) / len(negative_periods)

    assert avg_solar_negative < avg_solar_normal, "Solar should be curtailed during negative pricing"

    # Verify that curtailment is actually happening (solar production < forecast)
    for i in negative_periods:
        assert solar_production[i] < solar_forecast[i], f"Solar should be curtailed in period {i}"
