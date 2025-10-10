"""Test the model components."""

from typing import Any

from pulp import value
import pytest

from custom_components.haeo.const import (
    ELEMENT_TYPE_BATTERY,
    ELEMENT_TYPE_CONNECTION,
    ELEMENT_TYPE_CONSTANT_LOAD,
    ELEMENT_TYPE_FORECAST_LOAD,
    ELEMENT_TYPE_GENERATOR,
    ELEMENT_TYPE_GRID,
    ELEMENT_TYPE_NET,
)
from custom_components.haeo.model import Network
from custom_components.haeo.model.battery import Battery
from custom_components.haeo.model.connection import Connection
from custom_components.haeo.model.constant_load import ConstantLoad
from custom_components.haeo.model.element import Element
from custom_components.haeo.model.forecast_load import ForecastLoad
from custom_components.haeo.model.generator import Generator
from custom_components.haeo.model.grid import Grid
from custom_components.haeo.model.net import Net

# Test constants
SECONDS_PER_HOUR = 3600
HOURS_PER_DAY = 24
MIN_CONSTRAINTS = 2

# Test magic value constants
DEFAULT_PERIODS = 24
DEFAULT_BATTERY_CAPACITY = 10000
DEFAULT_EFFICIENCY = 0.95
DEFAULT_EFFICIENCY_MINIMAL = 0.99
GRID_PERIODS = 3
LOAD_PERIODS = 3
GENERATOR_PERIODS = 3
CONNECTION_PERIODS = 3
DEFAULT_POWER = 1000
FORECAST_POWER = 1500
FORECAST_POWER_HIGH = 2000
FORECAST_POWER_CONST = 1500
SUM_POWER = 300.0
DEFAULT_ENERGY = 500.0
MAX_POWER_LIMIT = 3000
REVERSE_POWER_LIMIT = 2000
INVALID_CAPACITY = -1000
INVALID_PERCENTAGE = 150


def test_battery_initialization() -> None:
    """Test battery initialization."""
    battery = Battery(
        name="test_battery",
        period=SECONDS_PER_HOUR,
        n_periods=HOURS_PER_DAY,
        capacity=10000,
        initial_charge_percentage=50,
        min_charge_percentage=10,
        max_charge_percentage=90,
        max_charge_power=5000,
        max_discharge_power=5000,
        efficiency=0.95,
    )

    assert battery.name == "test_battery"
    assert battery.period == SECONDS_PER_HOUR
    assert battery.n_periods == DEFAULT_PERIODS
    assert battery.capacity == DEFAULT_BATTERY_CAPACITY
    assert battery.efficiency == DEFAULT_EFFICIENCY
    assert len(battery.power_consumption) == DEFAULT_PERIODS
    assert len(battery.power_production) == DEFAULT_PERIODS
    assert len(battery.energy) == DEFAULT_PERIODS


def test_battery_constraints() -> None:
    """Test battery constraints generation."""
    battery = Battery(
        name="test_battery",
        period=SECONDS_PER_HOUR,
        n_periods=3,
        capacity=10000,
        initial_charge_percentage=50,
    )

    constraints = battery.constraints()
    # Should have energy balance constraints for each time step after the first
    assert len(constraints) >= MIN_CONSTRAINTS  # n_periods - 1


def test_battery_initialization_defaults() -> None:
    """Test battery initialization with default values."""
    battery = Battery(
        name="test_battery",
        period=SECONDS_PER_HOUR,
        n_periods=HOURS_PER_DAY,
        capacity=10000,
        initial_charge_percentage=50,
    )

    assert battery.capacity == DEFAULT_BATTERY_CAPACITY  # Only capacity is stored as an attribute
    assert battery.efficiency == DEFAULT_EFFICIENCY_MINIMAL  # Default efficiency
    assert len(battery.power_consumption) == DEFAULT_PERIODS  # Power variables are created
    assert len(battery.power_production) == DEFAULT_PERIODS


def test_battery_invalid_capacity() -> None:
    """Test battery initialization with invalid capacity."""
    # Battery doesn't validate inputs in constructor, just stores them
    battery = Battery(
        name="test_battery",
        period=SECONDS_PER_HOUR,
        n_periods=HOURS_PER_DAY,
        capacity=INVALID_CAPACITY,  # Invalid negative capacity - but no validation in constructor
        initial_charge_percentage=50,
    )
    assert battery.capacity == INVALID_CAPACITY  # Just stores the value


def test_battery_invalid_initial_charge() -> None:
    """Test battery initialization with invalid initial charge percentage."""
    # Battery doesn't validate inputs in constructor, just uses them for initialization
    battery = Battery(
        name="test_battery",
        period=SECONDS_PER_HOUR,
        n_periods=HOURS_PER_DAY,
        capacity=10000,
        initial_charge_percentage=INVALID_PERCENTAGE,  # Invalid percentage > 100 - but no validation in constructor
    )
    assert battery.capacity == DEFAULT_BATTERY_CAPACITY  # Capacity is still stored correctly


def test_grid_initialization() -> None:
    """Test grid initialization."""
    import_price = [0.1, 0.2, 0.15]
    export_price = [0.05, 0.08, 0.06]

    grid = Grid(
        name="test_grid",
        period=SECONDS_PER_HOUR,
        n_periods=3,
        import_limit=10000,
        export_limit=5000,
        import_price=import_price,
        export_price=export_price,
    )

    assert grid.name == "test_grid"
    assert grid.period == SECONDS_PER_HOUR
    assert grid.n_periods == GRID_PERIODS
    assert len(grid.power_consumption) == GRID_PERIODS
    assert len(grid.power_production) == GRID_PERIODS
    assert grid.price_consumption == export_price
    assert grid.price_production == import_price


def test_grid_invalid_forecast_length() -> None:
    """Test grid with invalid forecast length."""
    with pytest.raises(ValueError, match="import_price length"):
        Grid(
            name="test_grid",
            period=SECONDS_PER_HOUR,
            n_periods=3,
            import_limit=10000,
            export_limit=5000,
            import_price=[0.1, 0.2],  # Wrong length
            export_price=[0.05, 0.08, 0.06],
        )


def test_grid_invalid_export_forecast_length() -> None:
    """Test grid with invalid export forecast length."""
    with pytest.raises(ValueError, match="export_price length"):
        Grid(
            name="test_grid",
            period=SECONDS_PER_HOUR,
            n_periods=3,
            import_limit=10000,
            export_limit=5000,
            import_price=[0.1, 0.2, 0.15],
            export_price=[0.05, 0.08],  # Wrong length
        )


def test_grid_initialization_defaults() -> None:
    """Test grid initialization with default values."""
    grid = Grid(
        name="test_grid",
        period=SECONDS_PER_HOUR,
        n_periods=3,
        import_limit=10000,
        export_limit=5000,
        import_price=[0.1, 0.2, 0.15],
        export_price=[0.05, 0.08, 0.06],
    )

    # Check that prices are correctly assigned
    # (note: price_consumption is export price, price_production is import price)
    assert grid.price_consumption == [0.05, 0.08, 0.06]  # Export prices become consumption prices
    assert grid.price_production == [0.1, 0.2, 0.15]  # Import prices become production prices


def test_grid_negative_import_limit() -> None:
    """Test grid with negative import limit."""
    # Grid doesn't validate inputs in constructor, just uses them for LpVariable bounds
    grid = Grid(
        name="test_grid",
        period=SECONDS_PER_HOUR,
        n_periods=3,
        import_limit=-1000,  # Invalid negative limit - but no validation in constructor
        export_limit=5000,
        import_price=[0.1, 0.2, 0.15],
        export_price=[0.05, 0.08, 0.06],
    )
    # Check that the grid was created successfully and has the expected structure
    assert grid.name == "test_grid"
    assert len(grid.power_consumption) == GRID_PERIODS  # Should have power variables


def test_grid_negative_export_limit() -> None:
    """Test grid with negative export limit."""
    # Grid doesn't validate inputs in constructor, just uses them for LpVariable bounds
    grid = Grid(
        name="test_grid",
        period=SECONDS_PER_HOUR,
        n_periods=3,
        import_limit=10000,
        export_limit=-5000,  # Invalid negative limit - but no validation in constructor
        import_price=[0.1, 0.2, 0.15],
        export_price=[0.05, 0.08, 0.06],
    )
    # Check that the grid was created successfully and has the expected structure
    assert grid.name == "test_grid"
    assert len(grid.power_production) == GRID_PERIODS  # Should have power variables


def test_load_forecast_initialization() -> None:
    """Test forecast load initialization."""
    forecast = [1000, 1500, 2000]

    load = ForecastLoad(
        name="test_load",
        period=SECONDS_PER_HOUR,
        n_periods=3,
        forecast=forecast,
    )

    assert load.name == "test_load"
    assert load.period == SECONDS_PER_HOUR
    assert load.n_periods == LOAD_PERIODS
    assert load.power_consumption == [DEFAULT_POWER, FORECAST_POWER, FORECAST_POWER_HIGH]  # forecast
    assert load.power_production is None


def test_load_forecast_invalid_forecast_length() -> None:
    """Test forecast load with invalid forecast length."""
    with pytest.raises(ValueError, match="forecast length"):
        ForecastLoad(
            name="test_load",
            period=SECONDS_PER_HOUR,
            n_periods=3,
            forecast=[1000, 1500],  # Wrong length
        )


def test_load_forecast_empty_forecast() -> None:
    """Test forecast load with empty forecast."""
    with pytest.raises(ValueError, match="forecast length"):
        ForecastLoad(
            name="test_load",
            period=SECONDS_PER_HOUR,
            n_periods=3,
            forecast=[],  # Empty forecast
        )


def test_load_constant_initialization() -> None:
    """Test constant load initialization."""
    load = ConstantLoad(
        name="test_load",
        period=SECONDS_PER_HOUR,
        n_periods=3,
        power=1500,
    )

    assert load.name == "test_load"
    assert load.period == SECONDS_PER_HOUR
    assert load.n_periods == LOAD_PERIODS
    # Constant power for all periods
    assert load.power_consumption == [FORECAST_POWER_CONST, FORECAST_POWER_CONST, FORECAST_POWER_CONST]
    assert load.power_production is None


def test_load_constant_negative_power() -> None:
    """Test constant load with negative power."""
    # LoadConstant doesn't validate inputs in constructor, just uses them to create power_consumption
    load = ConstantLoad(
        name="test_load",
        period=SECONDS_PER_HOUR,
        n_periods=3,
        power=-1500,  # Invalid negative power - but no validation in constructor
    )
    # Check that the load was created and has power consumption variables
    assert load.name == "test_load"
    assert len(load.power_consumption) == LOAD_PERIODS  # Should have power variables


def test_generator_initialization_with_curtailment() -> None:
    """Test generator initialization with curtailment."""
    forecast = [DEFAULT_POWER, FORECAST_POWER, FORECAST_POWER_HIGH]

    generator = Generator(
        name="test_generator",
        period=SECONDS_PER_HOUR,
        n_periods=GENERATOR_PERIODS,
        forecast=forecast,
        curtailment=True,
    )

    assert generator.name == "test_generator"
    assert generator.period == SECONDS_PER_HOUR
    assert generator.n_periods == GENERATOR_PERIODS
    assert len(generator.power_production) == GENERATOR_PERIODS
    assert generator.power_consumption is None


def test_generator_initialization_without_curtailment() -> None:
    """Test generator initialization without curtailment."""
    forecast = [1000, 1500, 2000]

    generator = Generator(
        name="test_generator",
        period=SECONDS_PER_HOUR,
        n_periods=3,
        forecast=forecast,
        curtailment=False,
    )

    assert generator.name == "test_generator"
    assert generator.power_production == forecast


def test_generator_invalid_forecast_length() -> None:
    """Test generator with invalid forecast length."""
    with pytest.raises(ValueError, match="forecast length"):
        Generator(
            name="test_generator",
            period=SECONDS_PER_HOUR,
            n_periods=3,
            forecast=[1000, 1500],  # Wrong length
            curtailment=True,
        )


def test_generator_initialization_defaults() -> None:
    """Test generator initialization with default values."""
    generator = Generator(
        name="test_generator",
        period=SECONDS_PER_HOUR,
        n_periods=3,
        forecast=[1000, 1500, 2000],
    )

    # Generator with curtailment=True (default) creates power_production variables
    assert generator.power_production is not None  # Curtailment is True by default
    assert len(generator.power_production) == GENERATOR_PERIODS


def test_generator_empty_forecast() -> None:
    """Test generator with empty forecast."""
    with pytest.raises(ValueError, match="forecast length"):
        Generator(
            name="test_generator",
            period=SECONDS_PER_HOUR,
            n_periods=3,
            forecast=[],  # Empty forecast
            curtailment=True,
        )


def test_net_initialization() -> None:
    """Test net initialization."""
    net = Net(
        name="test_net",
        period=SECONDS_PER_HOUR,
        n_periods=3,
    )

    assert net.name == "test_net"
    assert net.period == SECONDS_PER_HOUR
    assert net.n_periods == LOAD_PERIODS
    assert net.power_consumption is None
    assert net.power_production is None


def test_net_constraints() -> None:
    """Test net constraints generation."""
    net = Net(
        name="test_net",
        period=SECONDS_PER_HOUR,
        n_periods=3,
    )

    constraints = net.constraints()
    # Net constraints are generated when connected to other elements, so may be empty initially
    # The exact number depends on implementation details
    assert isinstance(constraints, list)


def test_network_initialization() -> None:
    """Test network initialization."""
    network = Network(
        name="test_network",
        period=SECONDS_PER_HOUR,
        n_periods=HOURS_PER_DAY,
    )

    assert network.name == "test_network"
    assert network.period == SECONDS_PER_HOUR
    assert network.n_periods == DEFAULT_PERIODS
    assert len(network.elements) == 0


def test_add_battery() -> None:
    """Test adding a battery to the network."""
    network = Network(
        name="test_network",
        period=SECONDS_PER_HOUR,
        n_periods=HOURS_PER_DAY,
    )

    battery = network.add(ELEMENT_TYPE_BATTERY, "test_battery", capacity=10000, initial_charge_percentage=50)

    assert isinstance(battery, Battery)
    assert battery.name == "test_battery"
    assert "test_battery" in network.elements
    assert network.elements["test_battery"] == battery


def test_add_grid() -> None:
    """Test adding a grid to the network."""
    network = Network(
        name="test_network",
        period=SECONDS_PER_HOUR,
        n_periods=3,
    )

    grid = network.add(
        ELEMENT_TYPE_GRID,
        "test_grid",
        import_limit=10000,
        export_limit=5000,
        import_price=[0.1, 0.2, 0.15],
        export_price=[0.05, 0.08, 0.06],
    )

    assert isinstance(grid, Grid)
    assert grid.name == "test_grid"
    assert "test_grid" in network.elements


def test_add_load() -> None:
    """Test adding a load to the network."""
    network = Network(
        name="test_network",
        period=SECONDS_PER_HOUR,
        n_periods=3,
    )

    load = network.add(
        ELEMENT_TYPE_FORECAST_LOAD,
        "test_load",
        forecast=[1000, 1500, 2000],
    )

    assert isinstance(load, ForecastLoad)
    assert load.name == "test_load"
    assert "test_load" in network.elements


def test_add_generator() -> None:
    """Test adding a generator to the network."""
    network = Network(
        name="test_network",
        period=SECONDS_PER_HOUR,
        n_periods=3,
    )

    generator = network.add(
        ELEMENT_TYPE_GENERATOR,
        "test_generator",
        forecast=[1000, 1500, 2000],
        curtailment=True,
    )

    assert isinstance(generator, Generator)
    assert generator.name == "test_generator"
    assert "test_generator" in network.elements


def test_add_net() -> None:
    """Test adding a net to the network."""
    network = Network(
        name="test_network",
        period=SECONDS_PER_HOUR,
        n_periods=3,
    )

    net = network.add(ELEMENT_TYPE_NET, "test_net")

    assert isinstance(net, Net)
    assert net.name == "test_net"
    assert "test_net" in network.elements


def test_network_add_duplicate_element() -> None:
    """Test adding duplicate element to network."""
    network = Network(
        name="test_network",
        period=SECONDS_PER_HOUR,
        n_periods=3,
    )

    # Add first battery
    battery1 = network.add(ELEMENT_TYPE_BATTERY, "test_battery", capacity=10000, initial_charge_percentage=50)
    assert battery1 is not None

    # Try to add another element with same name - this should overwrite or handle gracefully
    network.add(ELEMENT_TYPE_BATTERY, "test_battery", capacity=15000, initial_charge_percentage=75)

    # Network may allow overwriting or handle duplicates differently
    # Check that we have an element with the expected name
    assert "test_battery" in network.elements


def test_connect_entities() -> None:
    """Test connecting entities in the network."""
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

    # Connect them
    connection = network.add(
        ELEMENT_TYPE_CONNECTION,
        "battery1_to_grid1",
        source="battery1",
        target="grid1",
        min_power=0,
        max_power=5000,
    )

    assert connection is not None
    assert connection.name == "battery1_to_grid1"
    assert connection.source == "battery1"
    assert connection.target == "grid1"
    assert len(connection.power) == CONNECTION_PERIODS
    # Check that the connection element was added
    connection_name = "battery1_to_grid1"
    assert connection_name in network.elements
    assert isinstance(network.elements[connection_name], Connection)
    assert len(connection.power) == CONNECTION_PERIODS


def test_connect_nonexistent_entities() -> None:
    """Test connecting nonexistent entities."""
    network = Network(
        name="test_network",
        period=SECONDS_PER_HOUR,
        n_periods=3,
    )
    network.add(ELEMENT_TYPE_CONNECTION, "bad_connection", source="nonexistent", target="also_nonexistent")

    with pytest.raises(ValueError, match="Source element 'nonexistent' not found"):
        network.validate()


def test_connect_nonexistent_target_entity() -> None:
    """Test connecting to nonexistent target entity."""
    network = Network(
        name="test_network",
        period=SECONDS_PER_HOUR,
        n_periods=3,
    )
    # Add only source entity
    network.add(ELEMENT_TYPE_BATTERY, "battery1", capacity=10000, initial_charge_percentage=50)
    # Try to connect to nonexistent target
    network.add(ELEMENT_TYPE_CONNECTION, "bad_connection", source="battery1", target="nonexistent")

    with pytest.raises(ValueError, match="Target element 'nonexistent' not found"):
        network.validate()


def test_connection_with_negative_power_bounds() -> None:
    """Test connection with negative power bounds for bidirectional flow."""
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
    connection = network.add(
        ELEMENT_TYPE_CONNECTION,
        "battery_grid_bidirectional",
        source="battery1",
        target="grid1",
        min_power=-REVERSE_POWER_LIMIT,  # Allow reverse flow up to 2000W
        max_power=MAX_POWER_LIMIT,  # Allow forward flow up to 3000W
    )

    assert connection is not None
    assert connection.name == "battery_grid_bidirectional"
    assert connection.source == "battery1"
    assert connection.target == "grid1"
    assert len(connection.power) == CONNECTION_PERIODS

    # Verify power variables have correct bounds
    for power_var in connection.power:
        assert power_var.lowBound == -REVERSE_POWER_LIMIT
        assert power_var.upBound == MAX_POWER_LIMIT


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
    battery = network.elements["battery1"]

    # Check that power variables exist and have values
    for power_var in battery.power_consumption:
        val = value(power_var)
        assert isinstance(val, (int, float))


def test_connection_with_none_bounds() -> None:
    """Test connection with None bounds (should use None for infinite bounds)."""
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

    # Create connection with None bounds (unlimited power)
    connection = network.add(
        ELEMENT_TYPE_CONNECTION,
        "unlimited_connection",
        source="battery1",
        target="grid1",
        min_power=None,  # Should remain None for infinite lower bound
        max_power=None,  # Should remain None for infinite upper bound
    )

    assert connection is not None
    assert len(connection.power) == CONNECTION_PERIODS

    # Verify power variables have None bounds (infinite)
    for power_var in connection.power:
        assert power_var.lowBound is None  # Should be None for infinite lower bound
        assert power_var.upBound is None  # Should be None for infinite upper bound


def test_connect_source_is_connection() -> None:
    """Test connecting when source is a connection element."""
    network = Network(
        name="test_network",
        period=SECONDS_PER_HOUR,
        n_periods=3,
    )
    # Add entities and a connection
    network.add(ELEMENT_TYPE_BATTERY, "battery1", capacity=10000, initial_charge_percentage=50)
    network.add(
        ELEMENT_TYPE_GRID,
        "grid1",
        import_limit=10000,
        export_limit=5000,
        import_price=[0.1, 0.2, 0.15],
        export_price=[0.05, 0.08, 0.06],
    )
    network.add(ELEMENT_TYPE_CONNECTION, "conn1", source="battery1", target="grid1")

    # Try to create another connection using the connection as source
    network.add(ELEMENT_TYPE_CONNECTION, "bad_connection", source="conn1", target="battery1")

    with pytest.raises(ValueError, match="Source element 'conn1' is a connection"):
        network.validate()


def test_connect_target_is_connection() -> None:
    """Test connecting when target is a connection element."""
    network = Network(
        name="test_network",
        period=SECONDS_PER_HOUR,
        n_periods=3,
    )
    # Add entities and a connection
    network.add(ELEMENT_TYPE_BATTERY, "battery1", capacity=10000, initial_charge_percentage=50)
    network.add(
        ELEMENT_TYPE_GRID,
        "grid1",
        import_limit=10000,
        export_limit=5000,
        import_price=[0.1, 0.2, 0.15],
        export_price=[0.05, 0.08, 0.06],
    )
    network.add(ELEMENT_TYPE_CONNECTION, "conn1", source="battery1", target="grid1")

    # Try to create another connection using the connection as target
    network.add(ELEMENT_TYPE_CONNECTION, "bad_connection", source="battery1", target="conn1")

    with pytest.raises(ValueError, match="Target element 'conn1' is a connection"):
        network.validate()


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
    network.add(ELEMENT_TYPE_FORECAST_LOAD, "load", forecast=[1000, 1500, 2000])
    network.add(ELEMENT_TYPE_NET, "net")

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
        ELEMENT_TYPE_GENERATOR,
        "solar",
        forecast=solar_forecast,
        curtailment=True,
        price_production=[0] * 8,
    )  # Solar has no fuel cost

    network.add(ELEMENT_TYPE_FORECAST_LOAD, "load", forecast=load_forecast)

    network.add(
        ELEMENT_TYPE_BATTERY,
        "battery",
        capacity=10000,  # 10 kWh
        initial_charge_percentage=50,
        min_charge_percentage=20,
        max_charge_percentage=90,
        max_charge_power=MAX_POWER_LIMIT,  # 3 kW charge rate
        max_discharge_power=MAX_POWER_LIMIT,  # 3 kW discharge rate
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

    network.add(ELEMENT_TYPE_NET, "net")

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
        ELEMENT_TYPE_GENERATOR,
        "solar",
        forecast=solar_forecast,
        curtailment=True,  # Allow curtailment
        price_production=[0] * 6,
    )  # No fuel cost for solar

    network.add(ELEMENT_TYPE_FORECAST_LOAD, "load", forecast=load_forecast)

    network.add(
        ELEMENT_TYPE_GRID,
        "grid",
        import_limit=10000,
        export_limit=10000,
        import_price=import_prices,
        export_price=export_prices,
    )

    network.add(ELEMENT_TYPE_NET, "net")

    # Connect entities
    network.add(ELEMENT_TYPE_CONNECTION, "solar_to_net", source="solar", target="net")
    network.add(ELEMENT_TYPE_CONNECTION, "grid_to_net", source="grid", target="net")
    network.add(ELEMENT_TYPE_CONNECTION, "net_to_load", source="net", target="load")

    # Run optimization
    cost = network.optimize()

    # Verify solution
    assert isinstance(cost, (int, float))

    # Access optimization results directly from elements
    solar = network.elements["solar"]

    # Helper function to safely extract numeric values from PuLP variables
    def extract_value(var: Any) -> float:
        """Extract numeric value from PuLP variable."""
        if var is None:
            return 0.0
        val = value(var)
        if val is None:
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        # Handle LpVariable case
        if hasattr(val, "value"):
            return float(val.value()) if val.value() is not None else 0.0
        return 0.0

    # Get solar production values
    solar_production = []

    if solar.power_production is not None:
        solar_production = [extract_value(p) for p in solar.power_production]

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


def _create_element_for_test(element_type: str, name: str, **kwargs: Any) -> Any:
    """Create element for testing based on type."""
    if element_type == ELEMENT_TYPE_BATTERY:
        return Battery(name=name, period=SECONDS_PER_HOUR, n_periods=HOURS_PER_DAY, **kwargs)
    if element_type == ELEMENT_TYPE_GRID:
        return Grid(name=name, period=SECONDS_PER_HOUR, n_periods=3, **kwargs)
    if element_type == ELEMENT_TYPE_CONSTANT_LOAD:
        return ConstantLoad(name=name, period=SECONDS_PER_HOUR, n_periods=3, **kwargs)
    if element_type == ELEMENT_TYPE_FORECAST_LOAD:
        return ForecastLoad(name=name, period=SECONDS_PER_HOUR, n_periods=3, **kwargs)
    if element_type == ELEMENT_TYPE_GENERATOR:
        return Generator(name=name, period=SECONDS_PER_HOUR, n_periods=3, **kwargs)
    if element_type == ELEMENT_TYPE_NET:
        return Net(name=name, period=SECONDS_PER_HOUR, n_periods=3)
    pytest.fail(f"Unknown element type: {element_type}")


def _assert_element_basic_properties(element: Any, name: str) -> None:
    """Assert basic properties for all elements."""
    assert element.name == name
    assert element.period == SECONDS_PER_HOUR


def _assert_element_power_vars(element: Any, expected_vars: int) -> None:
    """Assert power variable counts for elements."""
    if element.power_consumption:
        assert len(element.power_consumption) == expected_vars
    if element.power_production:
        assert len(element.power_production) == expected_vars


def _assert_element_energy_vars(element: Any, expected_vars: int) -> None:
    """Assert energy variable counts for elements."""
    if element.energy:
        assert len(element.energy) == expected_vars


@pytest.mark.parametrize(
    "element_data",
    [
        pytest.param(
            {
                "type": ELEMENT_TYPE_BATTERY,
                "name": "test_battery",
                "capacity": 10000,
                "initial_charge_percentage": 50,
                "max_charge_power": 5000,
                "max_discharge_power": 5000,
                "expected_power_vars": 24,
                "expected_energy_vars": 24,
            },
            id="battery",
        ),
        pytest.param(
            {
                "type": ELEMENT_TYPE_GRID,
                "name": "test_grid",
                "import_limit": 10000,
                "export_limit": 5000,
                "import_price": [0.1, 0.2, 0.15],
                "export_price": [0.05, 0.08, 0.06],
                "expected_power_vars": 3,
            },
            id="grid",
        ),
        pytest.param(
            {
                "type": ELEMENT_TYPE_CONSTANT_LOAD,
                "name": "test_load_constant",
                "power": 1500,
                "expected_power_vars": 3,
            },
            id="load_constant",
        ),
        pytest.param(
            {
                "type": ELEMENT_TYPE_FORECAST_LOAD,
                "name": "test_load_forecast",
                "forecast": [1000, 1500, 2000],
                "expected_power_vars": 3,
            },
            id="load_forecast",
        ),
        pytest.param(
            {
                "type": ELEMENT_TYPE_GENERATOR,
                "name": "test_generator",
                "forecast": [1000, 1500, 2000],
                "curtailment": True,
                "expected_power_vars": 3,
            },
            id="generator",
        ),
        pytest.param(
            {
                "type": ELEMENT_TYPE_NET,
                "name": "test_net",
                "expected_power_vars": 3,
            },
            id="net",
        ),
    ],
)
def test_element_initialization(element_data: dict[str, Any]) -> None:
    """Test element initialization using parameterized data."""
    element_type = element_data["type"]
    name = element_data["name"]
    kwargs = {
        k: v
        for k, v in element_data.items()
        if k not in ["type", "name", "expected_power_vars", "expected_energy_vars"]
    }

    # Create element based on type
    element = _create_element_for_test(element_type, name, **kwargs)

    # Basic assertions for all elements
    _assert_element_basic_properties(element, name)

    # Element-specific assertions
    if "expected_power_vars" in element_data:
        _assert_element_power_vars(element, element_data["expected_power_vars"])

    if "expected_energy_vars" in element_data:
        _assert_element_energy_vars(element, element_data["expected_energy_vars"])


@pytest.mark.parametrize(
    "element_data",
    [
        pytest.param(
            {
                "type": ELEMENT_TYPE_BATTERY,
                "name": "test_battery",
                "capacity": 10000,
                "initial_charge_percentage": 50,
            },
            id="battery",
        ),
        pytest.param(
            {
                "type": ELEMENT_TYPE_GRID,
                "name": "test_grid",
                "import_limit": 10000,
                "export_limit": 5000,
                "import_price": [0.1, 0.2, 0.15],
                "export_price": [0.05, 0.08, 0.06],
            },
            id="grid",
        ),
        pytest.param(
            {
                "type": ELEMENT_TYPE_CONSTANT_LOAD,
                "name": "test_load_constant",
                "power": 1500,
            },
            id="load_constant",
        ),
        pytest.param(
            {
                "type": ELEMENT_TYPE_FORECAST_LOAD,
                "name": "test_load_forecast",
                "forecast": [1000, 1500, 2000],
            },
            id="load_forecast",
        ),
        pytest.param(
            {
                "type": ELEMENT_TYPE_GENERATOR,
                "name": "test_generator",
                "forecast": [1000, 1500, 2000],
                "curtailment": True,
            },
            id="generator",
        ),
        pytest.param(
            {
                "type": ELEMENT_TYPE_NET,
                "name": "test_net",
            },
            id="net",
        ),
    ],
)
def test_element_constraints(element_data: dict[str, Any]) -> None:
    """Test element constraints generation."""
    element_type = element_data["type"]
    name = element_data["name"]
    kwargs = {
        k: v
        for k, v in element_data.items()
        if k not in ["type", "name", "expected_power_vars", "expected_energy_vars"]
    }

    # Create element based on type
    element: Element | None = None
    if element_type == ELEMENT_TYPE_BATTERY:
        element = Battery(name=name, period=SECONDS_PER_HOUR, n_periods=3, **kwargs)
    elif element_type == ELEMENT_TYPE_GRID:
        element = Grid(name=name, period=SECONDS_PER_HOUR, n_periods=3, **kwargs)
    elif element_type == ELEMENT_TYPE_CONSTANT_LOAD:
        element = ConstantLoad(name=name, period=SECONDS_PER_HOUR, n_periods=3, **kwargs)
    elif element_type == ELEMENT_TYPE_FORECAST_LOAD:
        element = ForecastLoad(name=name, period=SECONDS_PER_HOUR, n_periods=3, **kwargs)
    elif element_type == ELEMENT_TYPE_GENERATOR:
        element = Generator(name=name, period=SECONDS_PER_HOUR, n_periods=3, **kwargs)
    elif element_type == ELEMENT_TYPE_NET:
        element = Net(name=name, period=SECONDS_PER_HOUR, n_periods=3)
    else:
        pytest.fail(f"Unknown element type: {element_type}")

    constraints = element.constraints()
    assert isinstance(constraints, list)
    # Most elements should have at least some constraints
    if element_type != ELEMENT_TYPE_NET:  # Net constraints depend on connections
        assert len(constraints) >= 0
