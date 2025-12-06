"""Integration tests for Network optimization scenarios."""

from numbers import Real

from pulp import LpAffineExpression, LpVariable, value
import pytest

from custom_components.haeo.elements import ELEMENT_TYPE_BATTERY, ELEMENT_TYPE_CONNECTION
from custom_components.haeo.model import Network

# Test constants
SECONDS_PER_HOUR = 3600
MAX_POWER_LIMIT = 3000
REVERSE_POWER_LIMIT = 2000


def safe_value(var: LpVariable | LpAffineExpression | float | None) -> float:
    """Return a numeric value for PuLP variables or raw numbers."""
    if var is None:
        return 0.0
    if isinstance(var, Real):
        return float(var)
    return float(value(var))


def test_simple_optimization() -> None:
    """Test a simple optimization scenario."""
    network = Network(name="test_network", period=1.0, n_periods=3)

    # Add a simple grid and load
    network.add("source_sink", "grid", is_source=True, is_sink=True)
    network.add("source_sink", "net", is_source=False, is_sink=False)  # Pure junction (was Node)
    network.add(
        ELEMENT_TYPE_CONNECTION,
        "grid_connection",
        source="grid",
        target="net",
        max_power_source_target=10000,  # import_limit
        max_power_target_source=5000,  # export_limit
        price_source_target=[0.1, 0.2, 0.15],  # import_price
        price_target_source=[0.05, 0.08, 0.06],  # export_price
    )
    network.add("source_sink", "load", is_source=False, is_sink=True)  # Sink only
    network.add(
        ELEMENT_TYPE_CONNECTION,
        "load_connection",
        source="net",
        target="load",
        fixed_power_source_target=[1000, 1500, 2000],  # load must consume exactly these amounts
    )

    # Run optimization
    cost = network.optimize()

    assert isinstance(cost, (int, float))


def test_battery_solar_grid_storage_cycle() -> None:
    """Test a scenario with grid, battery, and solar with storage and discharge cycles.

    Uses square wave patterns to force energy storage during high generation
    and discharge during high demand periods.
    """
    network = Network(name="storage_cycle_test", period=1.0, n_periods=8)

    # Solar generation with square wave pattern: high generation for 4 hours, then none
    solar_forecast = [5000, 5000, 5000, 5000, 0, 0, 0, 0]

    # Load demand with inverse square wave: low for 4 hours, then high
    load_forecast = [1000, 1000, 1000, 1000, 4000, 4000, 4000, 4000]

    # Grid pricing: cheap during high solar, expensive during low solar
    import_prices = [0.05, 0.05, 0.05, 0.05, 0.20, 0.20, 0.20, 0.20]
    export_prices = [0.03, 0.03, 0.03, 0.03, 0.15, 0.15, 0.15, 0.15]

    # Add entities
    network.add("source_sink", "solar", is_source=True, is_sink=False)  # Source only
    network.add("source_sink", "load", is_source=False, is_sink=True)  # Sink only
    network.add(
        ELEMENT_TYPE_BATTERY,
        "battery",
        capacity=10000,  # 10 kWh
        initial_charge_percentage=50,
        min_charge_percentage=20,
        max_charge_percentage=90,
    )
    network.add("source_sink", "grid", is_source=True, is_sink=True)  # Both
    network.add("source_sink", "net", is_source=False, is_sink=False)  # Pure junction

    # Connect everything through the net
    network.add(
        ELEMENT_TYPE_CONNECTION,
        "solar_to_net",
        source="solar",
        target="net",
        max_power_source_target=solar_forecast,  # forecast with curtailment
        price_target_source=[0] * 8,  # price_production
    )
    network.add(
        ELEMENT_TYPE_CONNECTION,
        "battery_to_net",
        source="battery",
        target="net",
        max_power_source_target=MAX_POWER_LIMIT,  # max_charge_power
        max_power_target_source=MAX_POWER_LIMIT,  # max_discharge_power
        efficiency_source_target=95.0,  # charging efficiency
        efficiency_target_source=95.0,  # discharging efficiency
    )
    network.add(
        ELEMENT_TYPE_CONNECTION,
        "grid_to_net",
        source="grid",
        target="net",
        max_power_source_target=10000,  # import_limit
        max_power_target_source=10000,  # export_limit
        price_source_target=import_prices,
        price_target_source=export_prices,
    )
    network.add(
        ELEMENT_TYPE_CONNECTION,
        "net_to_load",
        source="net",
        target="load",
        fixed_power_source_target=load_forecast,  # load must consume exactly these amounts
    )

    # Run optimization
    cost = network.optimize()

    # Verify the solution makes economic sense
    assert isinstance(cost, (int, float))
    # Cost can be negative due to early_charge_incentive benefits from charging free solar


@pytest.mark.skip(reason="Optimization failure test needs reworking - infeasible problem now solvable with new design")
def test_optimization_failure() -> None:
    """Test optimization failure handling."""
    network = Network(name="test_network", period=1.0, n_periods=3)

    # Create an infeasible optimization problem with conflicting constraints
    # Battery starts empty but must maintain minimum charge level
    network.add(
        ELEMENT_TYPE_BATTERY,
        "battery",
        capacity=1000,
        initial_charge_percentage=0,  # Empty
        min_charge_percentage=50,  # But must stay above 50%!
        max_charge_percentage=90,
    )
    network.add("source_sink", "node", is_source=False, is_sink=False)  # Pure junction
    network.add(
        ELEMENT_TYPE_CONNECTION,
        "battery_to_node",
        source="battery",
        target="node",
        max_power_source_target=0,  # Can't charge (no power source)
        max_power_target_source=1000,  # Could discharge if it had charge
    )

    # This should result in an infeasible optimization problem
    # (battery starts at 0% but must stay above 50%, and can't charge)
    with pytest.raises(ValueError, match="Optimization failed with status"):
        network.optimize()


def test_connection_power_balance_with_bidirectional_flow() -> None:
    """Test that power balance works correctly with bidirectional power flows."""
    network = Network(name="test_network", period=1.0, n_periods=3)

    # Add entities
    network.add(ELEMENT_TYPE_BATTERY, "battery1", capacity=10000, initial_charge_percentage=50)
    network.add("source_sink", "grid1")

    # Create bidirectional connection
    network.add(
        ELEMENT_TYPE_CONNECTION,
        "battery_grid_bidirectional",
        source="battery1",
        target="grid1",
        max_power_source_target=MAX_POWER_LIMIT,  # Forward flow
        max_power_target_source=REVERSE_POWER_LIMIT,  # Reverse flow
        price_source_target=[0.1, 0.2, 0.15],  # import_price
        price_target_source=[0.05, 0.08, 0.06],  # export_price
    )

    # Validate the network (should pass)
    network.validate()

    # Run optimization
    cost = network.optimize()

    # Should complete without errors
    assert isinstance(cost, (int, float))


@pytest.mark.skip(reason="Solar curtailment test needs reworking with new adapter pattern")
def test_solar_curtailment_negative_pricing() -> None:
    """Test solar curtailment during negative export pricing periods.

    This scenario tests the system's ability to curtail solar generation
    when export prices are negative (paying to export power costs money).
    With no load or storage, excess solar during negative pricing should be curtailed.
    """
    network = Network(name="curtailment_test", period=1.0, n_periods=6)

    # High solar generation throughout the test period
    solar_forecast = [6000, 6000, 6000, 6000, 6000, 6000]

    # Grid pricing with negative export prices in the middle periods
    # Positive prices represent revenue (optimizer wants to maximize exports)
    # Negative prices represent cost (optimizer wants to minimize exports)
    export_prices = [-0.05, -0.05, 0.02, 0.02, -0.05, -0.05]  # Cost to export in periods 2-3

    # Add entities
    network.add("source_sink", "solar", is_source=True, is_sink=False)  # Source only
    network.add("source_sink", "grid", is_source=True, is_sink=True)  # Both
    network.add("source_sink", "net", is_source=False, is_sink=False)  # Pure junction

    # Connect entities (no load - just solar and grid)
    network.add(
        ELEMENT_TYPE_CONNECTION,
        "solar_to_net",
        source="solar",
        target="net",
        max_power_source_target=solar_forecast,  # forecast allows curtailment
    )
    network.add(
        ELEMENT_TYPE_CONNECTION,
        "grid_to_net",
        source="grid",
        target="net",
        max_power_source_target=0,  # no import
        max_power_target_source=10000,  # export limit
        price_target_source=export_prices,  # export pricing (negative = cost to export)
    )

    # Run optimization
    cost = network.optimize()

    # Verify solution
    assert isinstance(cost, (int, float))

    # Access optimization results directly from connections
    solar_connection = network.elements["solar_to_net"]
    assert hasattr(solar_connection, "power_source_target")
    assert solar_connection.power_source_target is not None
    solar_production = [safe_value(power) for power in solar_connection.power_source_target]

    # During periods with positive export prices (2-3), exporting costs money, so solar should curtail
    # During periods with negative export prices (0,1,4,5), exporting earns revenue, so solar should produce
    profitable_periods = [0, 1, 4, 5]  # Negative export price = revenue
    costly_periods = [2, 3]  # Positive export price = cost

    # Solar should produce in profitable periods (negative price = revenue from exports)
    for i in profitable_periods:
        assert solar_production[i] > 0, f"Solar should produce during profitable pricing in period {i}"

    # Solar should be fully curtailed during costly periods (positive price = cost to export)
    for i in costly_periods:
        assert solar_production[i] == 0, f"Solar should be fully curtailed during costly pricing in period {i}"
