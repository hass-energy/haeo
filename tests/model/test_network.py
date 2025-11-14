"""Unit tests for Network class."""

from typing import cast
from unittest.mock import Mock

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
from custom_components.haeo.model.connection import Connection
from custom_components.haeo.model.element import Element
from custom_components.haeo.model.grid import Grid
from custom_components.haeo.model.load import Load
from custom_components.haeo.model.node import Node
from custom_components.haeo.model.photovoltaics import Photovoltaics

# Test constants
SECONDS_PER_HOUR = 3600
HOURS_PER_DAY = 24
DEFAULT_PERIODS = 24
CONNECTION_PERIODS = 3
MAX_POWER_LIMIT = 3000
REVERSE_POWER_LIMIT = 2000


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
        ELEMENT_TYPE_LOAD,
        "test_load",
        forecast=[1000, 1500, 2000],
    )

    assert isinstance(load, Load)
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
        ELEMENT_TYPE_PHOTOVOLTAICS,
        "test_generator",
        forecast=[1000, 1500, 2000],
        curtailment=True,
    )

    assert isinstance(generator, Photovoltaics)
    assert generator.name == "test_generator"
    assert "test_generator" in network.elements


def test_add_net() -> None:
    """Test adding a node to the network."""
    network = Network(
        name="test_network",
        period=SECONDS_PER_HOUR,
        n_periods=3,
    )

    net = network.add(ELEMENT_TYPE_NODE, "test_net")

    assert isinstance(net, Node)
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

    # Try to add another element with same name
    network.add(ELEMENT_TYPE_BATTERY, "test_battery", capacity=15000, initial_charge_percentage=75)

    # Network handles duplicates
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
    connection = cast(
        "Connection",
        network.add(
            ELEMENT_TYPE_CONNECTION,
            "battery1_to_grid1",
            source="battery1",
            target="grid1",
            max_power_source_target=5000,
        ),
    )

    assert connection is not None
    assert connection.name == "battery1_to_grid1"
    assert connection.source == "battery1"
    assert connection.target == "grid1"
    assert connection.power_source_target is not None
    assert connection.power_target_source is not None
    assert len(connection.power_source_target) == CONNECTION_PERIODS
    assert len(connection.power_target_source) == CONNECTION_PERIODS
    # Check that the connection element was added
    connection_name = "battery1_to_grid1"
    assert connection_name in network.elements
    assert isinstance(network.elements[connection_name], Connection)


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
    """Test connection with bidirectional power flow limits."""
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
    connection = cast(
        "Connection",
        network.add(
            ELEMENT_TYPE_CONNECTION,
            "battery_grid_bidirectional",
            source="battery1",
            target="grid1",
            max_power_source_target=MAX_POWER_LIMIT,  # Forward flow up to 3000W
            max_power_target_source=REVERSE_POWER_LIMIT,  # Reverse flow up to 2000W
        ),
    )

    assert connection is not None
    assert connection.name == "battery_grid_bidirectional"
    assert connection.source == "battery1"
    assert connection.target == "grid1"
    assert connection.power_source_target is not None
    assert connection.power_target_source is not None
    assert len(connection.power_source_target) == CONNECTION_PERIODS
    assert len(connection.power_target_source) == CONNECTION_PERIODS

    # Verify power variables have correct bounds
    for power_var in connection.power_source_target:
        assert power_var.lowBound == 0
        assert power_var.upBound == MAX_POWER_LIMIT

    for power_var in connection.power_target_source:
        assert power_var.lowBound == 0
        assert power_var.upBound == REVERSE_POWER_LIMIT


def test_connection_with_none_bounds() -> None:
    """Test connection with None bounds for unlimited power flow."""
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

    # Create connection with None bounds (unlimited power in both directions)
    connection = cast(
        "Connection",
        network.add(
            ELEMENT_TYPE_CONNECTION,
            "unlimited_connection",
            source="battery1",
            target="grid1",
            # No power limits specified - unlimited in both directions
        ),
    )

    assert connection is not None
    assert connection.power_source_target is not None
    assert connection.power_target_source is not None
    assert len(connection.power_source_target) == CONNECTION_PERIODS
    assert len(connection.power_target_source) == CONNECTION_PERIODS

    # Verify power variables have None upper bounds (infinite)
    for power_var in connection.power_source_target:
        assert power_var.lowBound == 0  # Always positive
        assert power_var.upBound is None  # Unlimited

    for power_var in connection.power_target_source:
        assert power_var.lowBound == 0  # Always positive
        assert power_var.upBound is None  # Unlimited


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


def test_network_constraint_generation_error() -> None:
    """Test that constraint generation errors are caught and wrapped with context."""
    network = Network(
        name="test_network",
        period=SECONDS_PER_HOUR,
        n_periods=3,
    )

    # Add a regular battery
    network.add(ELEMENT_TYPE_BATTERY, "battery", capacity=10000, initial_charge_percentage=50)

    # Mock an element to raise an exception during constraint generation
    mock_element = Mock(spec=Element)
    mock_element.name = "failing_element"
    mock_element.constraints.side_effect = RuntimeError("Constraint generation failed")
    network.elements["failing_element"] = mock_element

    # Should wrap the error with context about which element failed
    with pytest.raises(ValueError, match="Failed to generate constraints for element 'failing_element'"):
        network.constraints()


def test_network_invalid_solver() -> None:
    """Test that invalid solver names raise clear errors."""
    network = Network(
        name="test_network",
        period=SECONDS_PER_HOUR,
        n_periods=3,
    )

    # Add simple network
    network.add(ELEMENT_TYPE_BATTERY, "battery", capacity=10000, initial_charge_percentage=50)
    network.add(ELEMENT_TYPE_NODE, "net")
    network.add(ELEMENT_TYPE_CONNECTION, "battery_to_net", source="battery", target="net")

    # Try to use non-existent solver
    with pytest.raises(ValueError, match="Failed to get solver 'NonExistentSolver'"):
        network.optimize(optimizer="NonExistentSolver")
