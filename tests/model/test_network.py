"""Unit tests for Network class."""

from typing import cast
from unittest.mock import Mock

import pytest

from custom_components.haeo.elements import (
    ELEMENT_TYPE_BATTERY,
    ELEMENT_TYPE_CONNECTION,
    ELEMENT_TYPE_GRID,
    ELEMENT_TYPE_NODE,
)
from custom_components.haeo.model import Network
from custom_components.haeo.model.connection import Connection
from custom_components.haeo.model.element import Element

# Test constants
HOURS_PER_DAY = 24
DEFAULT_PERIODS = 24
CONNECTION_PERIODS = 3


def test_network_initialization() -> None:
    """Test network initialization."""
    network = Network(
        name="test_network",
        periods=[1.0] * HOURS_PER_DAY,
    )

    assert network.name == "test_network"
    assert network.periods == [1.0] * DEFAULT_PERIODS  # Periods in hours
    assert network.n_periods == DEFAULT_PERIODS
    assert len(network.elements) == 0


def test_network_add_duplicate_element() -> None:
    """Test adding duplicate element to network."""
    network = Network(
        name="test_network",
        periods=[1.0] * 3,
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
        periods=[1.0] * 3,
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
        periods=[1.0] * 3,
    )
    network.add(ELEMENT_TYPE_CONNECTION, "bad_connection", source="nonexistent", target="also_nonexistent")

    with pytest.raises(ValueError, match="Source element 'nonexistent' not found"):
        network.validate()


def test_connect_nonexistent_target_entity() -> None:
    """Test connecting to nonexistent target entity."""
    network = Network(
        name="test_network",
        periods=[1.0] * 3,
    )
    # Add only source entity
    network.add(ELEMENT_TYPE_BATTERY, "battery1", capacity=10000, initial_charge_percentage=50)
    # Try to connect to nonexistent target
    network.add(ELEMENT_TYPE_CONNECTION, "bad_connection", source="battery1", target="nonexistent")

    with pytest.raises(ValueError, match="Target element 'nonexistent' not found"):
        network.validate()


def test_connect_source_is_connection() -> None:
    """Test connecting when source is a connection element."""
    network = Network(
        name="test_network",
        periods=[1.0] * 3,
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
        periods=[1.0] * 3,
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
        periods=[1.0] * 3,
    )

    # Add a regular battery
    network.add(ELEMENT_TYPE_BATTERY, "battery", capacity=10000, initial_charge_percentage=50)

    # Mock an element to raise an exception during constraint generation
    mock_element = Mock(spec=Element)
    mock_element.name = "failing_element"
    mock_element.build = Mock()
    mock_element.power_balance_constraints = {}
    mock_element.power_consumption = None
    mock_element.power_production = None
    mock_element.cost = Mock(return_value=0)
    mock_element.constraints.side_effect = RuntimeError("Constraint generation failed")
    network.elements["failing_element"] = mock_element

    # Should wrap the error with context about which element failed
    with pytest.raises(ValueError, match="Failed to get constraints for element 'failing_element'"):
        network.constraints()


def test_network_invalid_solver() -> None:
    """Test that invalid solver names raise clear errors."""
    network = Network(
        name="test_network",
        periods=[1.0] * 3,
    )

    # Add simple network
    network.add(ELEMENT_TYPE_BATTERY, "battery", capacity=10000, initial_charge_percentage=50)
    network.add(ELEMENT_TYPE_NODE, "net")
    network.add(ELEMENT_TYPE_CONNECTION, "battery_to_net", source="battery", target="net")

    # Try to use non-existent solver
    with pytest.raises(ValueError, match="Failed to get solver 'NonExistentSolver'"):
        network.optimize(optimizer="NonExistentSolver")


def test_network_optimize_validates_before_running() -> None:
    """Test that optimize() calls validate() and catches validation errors."""
    network = Network(
        name="test_network",
        periods=[1.0] * 3,
    )

    # Add elements but create an invalid connection
    network.add(ELEMENT_TYPE_NODE, "node1")
    network.add(ELEMENT_TYPE_CONNECTION, "bad_conn", source="node1", target="nonexistent_node")

    # Should raise validation error when trying to optimize
    with pytest.raises(ValueError, match="Target element 'nonexistent_node' not found"):
        network.optimize()


def test_network_optimize_build_constraints_error() -> None:
    """Test that optimize() catches and wraps build_constraints errors."""
    network = Network(
        name="test_network",
        periods=[1.0] * 3,
    )

    # Add a regular element
    network.add(ELEMENT_TYPE_NODE, "node1")

    # Mock an element that raises an exception during build_constraints
    mock_element = Mock(spec=Element)
    mock_element.build_constraints.side_effect = RuntimeError("Build failed")
    mock_element.constraints.return_value = []
    mock_element.cost.return_value = []
    network.elements["failing_element"] = mock_element

    # Should wrap the error with context about which element failed
    with pytest.raises(ValueError, match="Failed to build constraints for element 'failing_element'"):
        network.optimize()
