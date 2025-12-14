"""Tests to improve coverage for element.py edge cases."""

from unittest.mock import Mock

from highspy import Highs
from highspy.highs import highs_linear_expression

from custom_components.haeo.model.connection import Connection
from custom_components.haeo.model.node import Node


def test_connection_power_with_target_end(solver: Highs) -> None:
    """Test connection_power when element is registered as target end of connection.

    This tests the elif end == "target" branch (line 74 in element.py).
    """
    h = solver

    # Create a simple node element
    node = Node(name="test_node", periods=[1.0] * 3, solver=h)

    # Create a mock connection with HiGHS variables
    mock_connection = Mock(spec=Connection)
    mock_connection.power_source_target = [h.addVariable(lb=0, name=f"power_st_{i}") for i in range(3)]
    mock_connection.power_target_source = [h.addVariable(lb=0, name=f"power_ts_{i}") for i in range(3)]
    mock_connection.efficiency_source_target = [0.95, 0.95, 0.95]
    mock_connection.efficiency_target_source = [0.90, 0.90, 0.90]

    # Register the connection with node as TARGET
    node.register_connection(mock_connection, "target")

    # Call connection_power - should use the "target" branch
    result = node.connection_power(0)

    # Result should be a highs_linear_expression
    assert isinstance(result, highs_linear_expression)


def test_connection_power_with_source_end(solver: Highs) -> None:
    """Test connection_power when element is registered as source end of connection.

    This tests the if end == "source" branch (line 69 in element.py).
    """
    h = solver

    # Create a simple node element
    node = Node(name="test_node", periods=[1.0] * 3, solver=h)

    # Create a mock connection with HiGHS variables
    mock_connection = Mock(spec=Connection)
    mock_connection.power_source_target = [h.addVariable(lb=0, name=f"power_st_{i}") for i in range(3)]
    mock_connection.power_target_source = [h.addVariable(lb=0, name=f"power_ts_{i}") for i in range(3)]
    mock_connection.efficiency_source_target = [0.95, 0.95, 0.95]
    mock_connection.efficiency_target_source = [0.90, 0.90, 0.90]

    # Register the connection with node as SOURCE
    node.register_connection(mock_connection, "source")

    # Call connection_power - should use the "source" branch
    result = node.connection_power(0)

    # Result should be a highs_linear_expression
    assert isinstance(result, highs_linear_expression)


def test_constraints_with_single_constraint(solver: Highs) -> None:
    """Test constraints() method when a single constraint (not a sequence) is stored.

    This tests the else branch (line 106 in element.py).
    """
    h = solver

    # Create a simple element
    element = Node(name="test_node", periods=[1.0] * 3, solver=h)

    # Create variables for constraints
    x = h.addVariable(lb=0, name="x")
    y = h.addVariable(lb=0, name="y")

    # Manually add a single constraint (not a list) for testing
    single_constraint = h.addConstr(x <= 10)
    element._constraints["single"] = single_constraint  # type: ignore[index]

    # Also add a list of constraints
    list_constraints = h.addConstrs([x <= 5, y <= 5])
    element._constraints["list"] = list_constraints  # type: ignore[index]

    # Get all constraints
    result = element.constraints()

    # Should have 3 constraints total: 1 single + 2 from list
    assert len(result) == 3
    assert single_constraint in result
    assert list_constraints[0] in result
    assert list_constraints[1] in result


def test_connection_power_with_multiple_connections(solver: Highs) -> None:
    """Test connection_power with multiple connections including both source and target ends."""
    h = solver

    # Create a simple node element
    node = Node(name="test_node", periods=[1.0] * 3, solver=h)

    # Create first mock connection (node as source)
    mock_conn1 = Mock(spec=Connection)
    mock_conn1.power_source_target = [h.addVariable(lb=0, name=f"conn1_st_{i}") for i in range(3)]
    mock_conn1.power_target_source = [h.addVariable(lb=0, name=f"conn1_ts_{i}") for i in range(3)]
    mock_conn1.efficiency_source_target = [0.95] * 3
    mock_conn1.efficiency_target_source = [0.90] * 3

    # Create second mock connection (node as target)
    mock_conn2 = Mock(spec=Connection)
    mock_conn2.power_source_target = [h.addVariable(lb=0, name=f"conn2_st_{i}") for i in range(3)]
    mock_conn2.power_target_source = [h.addVariable(lb=0, name=f"conn2_ts_{i}") for i in range(3)]
    mock_conn2.efficiency_source_target = [0.98] * 3
    mock_conn2.efficiency_target_source = [0.92] * 3

    # Register both connections
    node.register_connection(mock_conn1, "source")
    node.register_connection(mock_conn2, "target")

    # Call connection_power - should combine both connections
    result = node.connection_power(0)

    # Result should be a highs_linear_expression
    assert isinstance(result, highs_linear_expression)
