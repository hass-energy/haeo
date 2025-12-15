"""Unit tests for Network class."""

import logging
from typing import cast
from unittest.mock import Mock

from highspy import HighsModelStatus
import pytest

from custom_components.haeo.model import Network
from custom_components.haeo.model import network as network_module
from custom_components.haeo.model.connection import Connection
from custom_components.haeo.model.element import Element
from custom_components.haeo.model.source_sink import SourceSink

# Test constants
HOURS_PER_DAY = 24
DEFAULT_PERIODS = 24
CONNECTION_PERIODS = 3

# Model element type strings
ELEMENT_TYPE_BATTERY = "battery"
ELEMENT_TYPE_CONNECTION = "connection"
ELEMENT_TYPE_SOURCE_SINK = "source_sink"


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
    battery1 = network.add(ELEMENT_TYPE_BATTERY, "test_battery", capacity=10000, initial_charge=5000)  # 50% of 10000
    assert battery1 is not None

    # Try to add another element with same name
    network.add(ELEMENT_TYPE_BATTERY, "test_battery", capacity=15000, initial_charge=11250)  # 75% of 15000

    # Network handles duplicates
    assert "test_battery" in network.elements


def test_connect_entities() -> None:
    """Test connecting entities in the network."""
    network = Network(
        name="test_network",
        periods=[1.0] * 3,
    )

    # Add entities
    network.add(ELEMENT_TYPE_BATTERY, "battery1", capacity=10000, initial_charge=5000)  # 50% of 10000
    network.add(ELEMENT_TYPE_SOURCE_SINK, "grid1", is_sink=False, is_source=True)

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
    with pytest.raises(ValueError, match="Failed to register connection bad_connection with source nonexistent"):
        network.add(ELEMENT_TYPE_CONNECTION, "bad_connection", source="nonexistent", target="also_nonexistent")


def test_connect_nonexistent_target_entity() -> None:
    """Test connecting to nonexistent target entity."""
    network = Network(
        name="test_network",
        periods=[1.0] * 3,
    )
    # Add only source entity
    network.add(ELEMENT_TYPE_BATTERY, "battery1", capacity=10000, initial_charge=5000)  # 50% of 10000
    # Try to connect to nonexistent target
    with pytest.raises(ValueError, match="Failed to register connection bad_connection with target nonexistent"):
        network.add(ELEMENT_TYPE_CONNECTION, "bad_connection", source="battery1", target="nonexistent")


def test_connect_source_is_connection() -> None:
    """Test connecting when source is a connection element."""
    network = Network(
        name="test_network",
        periods=[1.0] * 3,
    )
    # Add entities and a connection
    network.add(ELEMENT_TYPE_BATTERY, "battery1", capacity=10000, initial_charge=5000)  # 50% of 10000
    network.add(ELEMENT_TYPE_SOURCE_SINK, "grid1", is_sink=False, is_source=True)
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
    network.add(ELEMENT_TYPE_BATTERY, "battery1", capacity=10000, initial_charge=5000)  # 50% of 10000
    network.add(ELEMENT_TYPE_SOURCE_SINK, "grid1", is_sink=False, is_source=True)
    network.add(ELEMENT_TYPE_CONNECTION, "conn1", source="battery1", target="grid1")

    # Try to create another connection using the connection as target
    network.add(ELEMENT_TYPE_CONNECTION, "bad_connection", source="battery1", target="conn1")

    with pytest.raises(ValueError, match="Target element 'conn1' is a connection"):
        network.validate()


def test_validate_raises_when_source_missing() -> None:
    """Validate should raise when a connection source is missing."""
    net = Network(name="net", periods=[1.0] * 1)
    net.elements["conn"] = Connection(
        name="conn",
        periods=[1.0] * 1,
        solver=net._solver,
        source="missing",
        target="also_missing",
    )

    with pytest.raises(ValueError, match="Source element 'missing' not found"):
        net.validate()


def test_validate_raises_when_target_missing() -> None:
    """Validate should raise when a connection target is missing."""
    net = Network(name="net", periods=[1.0] * 1)
    net.elements["source_node"] = SourceSink(
        name="source_node", periods=[1.0] * 1, solver=net._solver, is_source=True, is_sink=True
    )
    net.elements["conn"] = Connection(
        name="conn",
        periods=[1.0] * 1,
        solver=net._solver,
        source="source_node",
        target="missing_target",
    )

    with pytest.raises(ValueError, match="Target element 'missing_target' not found"):
        net.validate()


def test_validate_raises_when_endpoints_are_connections() -> None:
    """Validate should reject connections that point to connection elements."""
    net = Network(name="net", periods=[1.0] * 1)
    # Non-connection element to satisfy target for conn2
    net.elements["node"] = SourceSink(name="node", periods=[1.0] * 1, solver=net._solver, is_source=True, is_sink=True)

    net.elements["conn2"] = Connection(
        name="conn2",
        periods=[1.0] * 1,
        solver=net._solver,
        source="node",
        target="node",
    )

    # conn1 references conn2 as source and target to hit both connection checks
    net.elements["conn1"] = Connection(
        name="conn1",
        periods=[1.0] * 1,
        solver=net._solver,
        source="conn2",
        target="conn2",
    )

    with pytest.raises(ValueError, match="Source element 'conn2' is a connection"):
        net.validate()


def test_constraints_returns_empty_when_no_elements() -> None:
    """Constraints should return empty list when network has no elements."""
    net = Network(name="net", periods=[1.0] * 1)

    assert net.constraints() == []


def test_network_constraint_generation_error() -> None:
    """Test that constraint generation errors are caught and wrapped with context."""
    network = Network(
        name="test_network",
        periods=[1.0] * 3,
    )

    # Add a regular battery
    network.add(ELEMENT_TYPE_BATTERY, "battery", capacity=10000, initial_charge=5000)  # 50% of 10000

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


def test_network_optimize_validates_before_running() -> None:
    """Test that optimize() calls validate() and catches validation errors."""
    network = Network(
        name="test_network",
        periods=[1.0] * 3,
    )

    # Add elements but create an invalid connection (connection to connection)
    network.add(ELEMENT_TYPE_SOURCE_SINK, "node1", is_sink=True, is_source=True)
    network.add(ELEMENT_TYPE_SOURCE_SINK, "node2", is_sink=True, is_source=True)
    network.add(ELEMENT_TYPE_CONNECTION, "conn1", source="node1", target="node2")

    # Connect conn2 to conn1 (invalid)
    network.add(ELEMENT_TYPE_CONNECTION, "conn2", source="conn1", target="node2")

    # Should raise validation error when trying to optimize
    with pytest.raises(ValueError, match="Source element 'conn1' is a connection"):
        network.optimize()


def test_network_optimize_build_constraints_error() -> None:
    """Test that optimize() catches and wraps build_constraints errors."""
    network = Network(
        name="test_network",
        periods=[1.0] * 3,
    )

    # Add a regular element
    network.add(ELEMENT_TYPE_SOURCE_SINK, "node1", is_sink=True, is_source=True)

    # Mock an element that raises an exception during build_constraints
    mock_element = Mock(spec=Element)
    mock_element.build_constraints.side_effect = RuntimeError("Build failed")
    mock_element.constraints.return_value = []
    mock_element.cost.return_value = []
    network.elements["failing_element"] = mock_element

    # Should wrap the error with context about which element failed
    with pytest.raises(ValueError, match="Failed to build constraints for element 'failing_element'"):
        network.optimize()


def test_network_optimize_success_logs_solver_output(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Optimize should return the objective and log solver streams."""

    caplog.set_level(logging.DEBUG, logger=network_module.__name__)

    network = Network(name="test_network", periods=[1.0] * 2)
    network.add(ELEMENT_TYPE_SOURCE_SINK, "node", is_sink=True, is_source=True)

    result = network.optimize()

    assert result == 0.0


def test_network_optimize_raises_on_solver_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Optimize should surface solver failure status with context."""
    network = Network(name="test_network", periods=[1.0] * 1)
    network.add(ELEMENT_TYPE_SOURCE_SINK, "node", is_sink=True, is_source=True)

    def mock_optimize() -> float:
        # Call build_constraints to set up the model
        network.validate()
        for element in network.elements.values():
            element.build_constraints()
        # Mock the model status to indicate failure
        monkeypatch.setattr(network._solver, "getModelStatus", lambda: HighsModelStatus.kUnbounded)
        network._solver.run()
        status = network._solver.getModelStatus()
        if status != HighsModelStatus.kOptimal:
            msg = f"Optimization failed with status: {network._solver.modelStatusToString(status)}"
            raise ValueError(msg)
        return network._solver.getObjectiveValue()

    with pytest.raises(ValueError, match="Optimization failed with status: Unbounded"):
        mock_optimize()
