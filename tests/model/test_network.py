"""Unit tests for Network class."""

import logging
from unittest.mock import Mock

from highspy import HighsModelStatus
import numpy as np
import pytest

from custom_components.haeo.model import Network
from custom_components.haeo.model import network as network_module
from custom_components.haeo.model.element import Element
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_BATTERY as ELEMENT_TYPE_BATTERY
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_CONNECTION as ELEMENT_TYPE_CONNECTION
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_NODE as ELEMENT_TYPE_NODE
from custom_components.haeo.model.elements.connection import Connection
from custom_components.haeo.model.elements.node import Node

# Test constants
HOURS_PER_DAY = 24
DEFAULT_PERIODS = 24
CONNECTION_PERIODS = 3


def test_network_initialization() -> None:
    """Test network initialization."""
    network = Network(
        name="test_network",
        periods=np.array([1.0] * HOURS_PER_DAY),
    )

    assert network.name == "test_network"
    np.testing.assert_array_equal(network.periods, [1.0] * DEFAULT_PERIODS)  # Periods in hours
    assert network.n_periods == DEFAULT_PERIODS
    assert len(network.elements) == 0


def test_network_add_duplicate_element() -> None:
    """Test adding duplicate element to network."""
    network = Network(
        name="test_network",
        periods=np.array([1.0] * 3),
    )

    # Add first battery
    battery1 = network.add(
        {"element_type": ELEMENT_TYPE_BATTERY, "name": "test_battery", "capacity": 10000, "initial_charge": 5000}
    )  # 50% of 10000
    assert battery1 is not None

    # Try to add another element with same name
    network.add(
        {"element_type": ELEMENT_TYPE_BATTERY, "name": "test_battery", "capacity": 15000, "initial_charge": 11250}
    )  # 75% of 15000

    # Network handles duplicates
    assert "test_battery" in network.elements


def test_connect_entities() -> None:
    """Test connecting entities in the network."""
    network = Network(
        name="test_network",
        periods=np.array([1.0] * 3),
    )

    # Add entities
    network.add({"element_type": ELEMENT_TYPE_BATTERY, "name": "battery1", "capacity": 10000, "initial_charge": 5000})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "grid1", "is_sink": False, "is_source": True})

    # Connect them
    connection = network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "battery1_to_grid1",
            "source": "battery1",
            "target": "grid1",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": 5000.0,
                }
            },
        }
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
        periods=np.array([1.0] * 3),
    )
    with pytest.raises(ValueError, match="Failed to register connection bad_connection with source nonexistent"):
        network.add(
            {
                "element_type": ELEMENT_TYPE_CONNECTION,
                "name": "bad_connection",
                "source": "nonexistent",
                "target": "also_nonexistent",
            }
        )


def test_connect_nonexistent_target_entity() -> None:
    """Test connecting to nonexistent target entity."""
    network = Network(
        name="test_network",
        periods=np.array([1.0] * 3),
    )
    # Add only source entity
    network.add({"element_type": ELEMENT_TYPE_BATTERY, "name": "battery1", "capacity": 10000, "initial_charge": 5000})
    # Try to connect to nonexistent target
    with pytest.raises(ValueError, match="Failed to register connection bad_connection with target nonexistent"):
        network.add(
            {
                "element_type": ELEMENT_TYPE_CONNECTION,
                "name": "bad_connection",
                "source": "battery1",
                "target": "nonexistent",
            }
        )


def test_connect_source_is_connection() -> None:
    """Test connecting when source is a connection element."""
    network = Network(
        name="test_network",
        periods=np.array([1.0] * 3),
    )
    # Add entities and a connection
    network.add({"element_type": ELEMENT_TYPE_BATTERY, "name": "battery1", "capacity": 10000, "initial_charge": 5000})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "grid1", "is_sink": False, "is_source": True})
    network.add({"element_type": ELEMENT_TYPE_CONNECTION, "name": "conn1", "source": "battery1", "target": "grid1"})

    # Try to create another connection using the connection as source
    network.add(
        {"element_type": ELEMENT_TYPE_CONNECTION, "name": "bad_connection", "source": "conn1", "target": "battery1"}
    )

    with pytest.raises(ValueError, match="Source element 'conn1' is a connection"):
        network.validate()


def test_connect_target_is_connection() -> None:
    """Test connecting when target is a connection element."""
    network = Network(
        name="test_network",
        periods=np.array([1.0] * 3),
    )
    # Add entities and a connection
    network.add({"element_type": ELEMENT_TYPE_BATTERY, "name": "battery1", "capacity": 10000, "initial_charge": 5000})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "grid1", "is_sink": False, "is_source": True})
    network.add({"element_type": ELEMENT_TYPE_CONNECTION, "name": "conn1", "source": "battery1", "target": "grid1"})

    # Try to create another connection using the connection as target
    network.add(
        {"element_type": ELEMENT_TYPE_CONNECTION, "name": "bad_connection", "source": "battery1", "target": "conn1"}
    )

    with pytest.raises(ValueError, match="Target element 'conn1' is a connection"):
        network.validate()


def test_validate_raises_when_source_missing() -> None:
    """Validate should raise when a connection source is missing."""
    net = Network(name="net", periods=np.array([1.0]))
    net.elements["conn"] = Connection(
        name="conn",
        periods=np.array([1.0]),
        solver=net._solver,
        source="missing",
        target="also_missing",
    )

    with pytest.raises(ValueError, match="Source element 'missing' not found"):
        net.validate()


def test_validate_raises_when_target_missing() -> None:
    """Validate should raise when a connection target is missing."""
    net = Network(name="net", periods=np.array([1.0]))
    net.elements["source_node"] = Node(
        name="source_node", periods=np.array([1.0]), solver=net._solver, is_source=True, is_sink=True
    )
    net.elements["conn"] = Connection(
        name="conn",
        periods=np.array([1.0]),
        solver=net._solver,
        source="source_node",
        target="missing_target",
    )

    with pytest.raises(ValueError, match="Target element 'missing_target' not found"):
        net.validate()


def test_validate_raises_when_endpoints_are_connections() -> None:
    """Validate should reject connections that point to connection elements."""
    net = Network(name="net", periods=np.array([1.0]))
    # Non-connection element to satisfy target for conn2
    net.elements["node"] = Node(name="node", periods=np.array([1.0]), solver=net._solver, is_source=True, is_sink=True)

    net.elements["conn2"] = Connection(
        name="conn2",
        periods=np.array([1.0]),
        solver=net._solver,
        source="node",
        target="node",
    )

    # conn1 references conn2 as source and target to hit both connection checks
    net.elements["conn1"] = Connection(
        name="conn1",
        periods=np.array([1.0]),
        solver=net._solver,
        source="conn2",
        target="conn2",
    )

    with pytest.raises(ValueError, match="Source element 'conn2' is a connection"):
        net.validate()


def test_constraints_returns_empty_when_no_elements() -> None:
    """Constraints should return empty dict when network has no elements."""
    net = Network(name="net", periods=np.array([1.0]))

    assert net.constraints() == {}


def test_network_constraint_generation_error() -> None:
    """Test that constraint generation errors are caught and wrapped with context."""
    network = Network(
        name="test_network",
        periods=np.array([1.0] * 3),
    )

    # Add a regular battery
    network.add({"element_type": ELEMENT_TYPE_BATTERY, "name": "battery", "capacity": 10000, "initial_charge": 5000})

    # Mock an element to raise an exception during constraints
    mock_element = Mock(spec=Element)
    mock_element.name = "failing_element"
    mock_element.build = Mock()
    mock_element.power_balance_constraints = {}
    mock_element.power_consumption = None
    mock_element.power_production = None
    mock_element.cost = Mock(return_value=None)
    mock_element.constraints.side_effect = RuntimeError("Constraint generation failed")
    network.elements["failing_element"] = mock_element

    # Should wrap the error with context about which element failed
    with pytest.raises(ValueError, match="Failed to apply constraints for element 'failing_element'"):
        network.optimize()


def test_network_optimize_validates_before_running() -> None:
    """Test that optimize() calls validate() and catches validation errors."""
    network = Network(
        name="test_network",
        periods=np.array([1.0] * 3),
    )

    # Add elements but create an invalid connection (connection to connection)
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "node1", "is_sink": True, "is_source": True})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "node2", "is_sink": True, "is_source": True})
    network.add({"element_type": ELEMENT_TYPE_CONNECTION, "name": "conn1", "source": "node1", "target": "node2"})

    # Connect conn2 to conn1 (invalid)
    network.add({"element_type": ELEMENT_TYPE_CONNECTION, "name": "conn2", "source": "conn1", "target": "node2"})

    # Should raise validation error when trying to optimize
    with pytest.raises(ValueError, match="Source element 'conn1' is a connection"):
        network.optimize()


def test_network_optimize_constraints_error() -> None:
    """Test that optimize() catches and wraps constraints errors."""
    network = Network(
        name="test_network",
        periods=np.array([1.0] * 3),
    )

    # Add a regular element
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "node1", "is_sink": True, "is_source": True})

    # Mock an element that raises an exception during constraints
    mock_element = Mock(spec=Element)
    mock_element.constraints.side_effect = RuntimeError("Build failed")
    mock_element.cost = Mock(return_value=None)
    network.elements["failing_element"] = mock_element

    # Should wrap the error with context about which element failed
    with pytest.raises(ValueError, match="Failed to apply constraints for element 'failing_element'"):
        network.optimize()


def test_network_optimize_success_logs_solver_output(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Optimize should return the objective and log solver streams."""

    caplog.set_level(logging.DEBUG, logger=network_module.__name__)

    network = Network(name="test_network", periods=np.array([1.0] * 2))
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "node", "is_sink": True, "is_source": True})

    result = network.optimize()

    assert result == 0.0


def test_log_callback_handles_empty_message() -> None:
    """Test _log_callback handles empty messages gracefully."""
    # Should not raise, just verify it doesn't crash
    Network._log_callback(0, "")
    Network._log_callback(1, "   ")  # Whitespace only


def test_network_optimize_raises_on_solver_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Optimize should surface solver failure status with context."""
    network = Network(name="test_network", periods=np.array([1.0]))
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "node", "is_sink": True, "is_source": True})

    def mock_optimize() -> float:
        # Call constraints to set up the model
        network.validate()
        for element in network.elements.values():
            element.constraints()
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


def test_network_optimize_raises_on_infeasible_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test optimize() raises ValueError when network optimization fails."""
    # Create a valid network
    network = Network(name="test_network", periods=np.array([1.0]))
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "node", "is_sink": True, "is_source": True})

    # Track if run() has been called
    run_called = False

    original_run = network._solver.run
    original_get_model_status = network._solver.getModelStatus

    def mock_run() -> None:
        nonlocal run_called
        original_run()
        run_called = True

    def mock_get_model_status() -> HighsModelStatus:
        # After run() is called, return a non-optimal status
        if run_called:
            return HighsModelStatus.kInfeasible
        return original_get_model_status()

    monkeypatch.setattr(network._solver, "run", mock_run)
    monkeypatch.setattr(network._solver, "getModelStatus", mock_get_model_status)

    # This should raise ValueError with the error message from optimize()
    with pytest.raises(ValueError, match="Optimization failed with status:"):
        network.optimize()


def test_add_soc_pricing_connection() -> None:
    """Test adding a SOC pricing connection via Network.add()."""
    network = Network(name="test_network", periods=np.array([1.0] * 3))

    network.add({"element_type": ELEMENT_TYPE_BATTERY, "name": "battery", "capacity": 10.0, "initial_charge": 5.0})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "node", "is_sink": True, "is_source": True})

    connection = network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "soc_pricing",
            "source": "battery",
            "target": "node",
            "segments": {
                "soc": {
                    "segment_type": "soc_pricing",
                    "discharge_energy_threshold": np.array([1.0, 1.0, 1.0]),
                    "discharge_energy_price": np.array([0.1, 0.1, 0.1]),
                }
            },
        }
    )

    assert connection is not None
    assert connection.name == "soc_pricing"
    assert "soc_pricing" in network.elements


def test_add_soc_pricing_connection_without_battery() -> None:
    """SOC pricing connection requires a battery endpoint."""
    network = Network(name="test_network", periods=np.array([1.0] * 3))

    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "source", "is_sink": False, "is_source": True})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "target", "is_sink": True, "is_source": False})

    with pytest.raises(TypeError, match="SOC pricing segment requires a battery element endpoint"):
        network.add(
            {
                "element_type": ELEMENT_TYPE_CONNECTION,
                "name": "soc_pricing",
                "source": "source",
                "target": "target",
                "segments": {
                    "soc": {
                        "segment_type": "soc_pricing",
                        "discharge_energy_threshold": np.array([1.0, 1.0, 1.0]),
                        "discharge_energy_price": np.array([0.1, 0.1, 0.1]),
                    }
                },
            }
        )


def test_network_cost_with_multiple_elements() -> None:
    """Test Network.cost() aggregates costs from multiple elements."""
    network = Network(name="test", periods=np.array([1.0, 1.0]))

    # Add two nodes
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "source", "is_source": True, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "target", "is_source": False, "is_sink": True})

    # Add two connections with pricing (each creates costs)
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "conn1",
            "source": "source",
            "target": "target",
            "segments": {
                "pricing": {"segment_type": "pricing", "price_source_target": np.array([10.0, 20.0])},
            },
        }
    )
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "conn2",
            "source": "target",
            "target": "source",
            "segments": {
                "pricing": {"segment_type": "pricing", "price_source_target": np.array([5.0, 10.0])},
            },
        }
    )

    # Get aggregated cost - should use Highs.qsum for multiple costs
    cost = network.cost()

    # Should return a combined ObjectiveCost
    assert cost is not None
    assert cost.primary is not None


def test_network_cost_returns_none_when_no_costs() -> None:
    """Test Network.cost() returns None when network has no objective terms."""
    network = Network(name="test", periods=np.array([1.0]))

    # Add a node (has no costs)
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "node", "is_source": True, "is_sink": True})

    # Should return None when no costs
    cost = network.cost()
    assert cost is None


def test_network_constraints_empty_when_no_elements() -> None:
    """Test Network.constraints() returns empty dict with no elements."""
    network = Network(name="test", periods=np.array([1.0]))

    # No elements added - should return empty dict
    constraints = network.constraints()
    assert constraints == {}
