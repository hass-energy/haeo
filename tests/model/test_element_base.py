"""Tests to improve coverage for element.py edge cases."""

from unittest.mock import Mock

from highspy import Highs
import pytest

from custom_components.haeo.model.connection import Connection
from custom_components.haeo.model.element import Element
from custom_components.haeo.model.node import Node


def test_connection_power_with_target_end(solver: Highs) -> None:
    """Test connection_power when element is registered as target end of connection.

    The connection's power_into_target provides the net power flowing into the element.
    """
    h = solver

    # Create a simple node element
    node = Node(name="test_node", periods=[1.0] * 3, solver=h)

    # Create power variables for the mock connection
    power_into_target = h.addVariables(3, lb=-10, ub=10, name_prefix="power_into_target_", out_array=True)

    # Create a mock connection
    mock_connection = Mock(spec=Connection)
    mock_connection.power_into_target = power_into_target

    # Register the connection with node as TARGET
    node.register_connection(mock_connection, "target")

    # Call connection_power - should return array for all periods
    result = node.connection_power()

    # Verify it's an array with 3 elements
    assert len(result) == 3

    # Set specific values and verify the calculation
    h.addConstr(power_into_target[0] == 7.5)
    h.minimize(result[0])  # Minimize to get the value
    assert h.val(result[0]) == pytest.approx(7.5)


def test_connection_power_with_source_end(solver: Highs) -> None:
    """Test connection_power when element is registered as source end of connection.

    The connection's power_into_source provides the net power flowing into the element.
    """
    h = solver

    # Create a simple node element
    node = Node(name="test_node", periods=[1.0] * 3, solver=h)

    # Create power variables for the mock connection
    power_into_source = h.addVariables(3, lb=-10, ub=10, name_prefix="power_into_source_", out_array=True)

    # Create a mock connection
    mock_connection = Mock(spec=Connection)
    mock_connection.power_into_source = power_into_source

    # Register the connection with node as SOURCE
    node.register_connection(mock_connection, "source")

    # Call connection_power - should return array for all periods
    result = node.connection_power()

    # Verify it's an array with 3 elements
    assert len(result) == 3

    # Set specific values and verify the calculation
    h.addConstr(power_into_source[1] == -2.0)
    h.minimize(result[1])  # Minimize to get the value
    assert h.val(result[1]) == pytest.approx(-2.0)


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
    """Test connection_power with multiple connections including both source and target ends.

    Total net power = sum of all connection power_into_* values.
    """
    h = solver

    # Create a simple node element
    node = Node(name="test_node", periods=[1.0] * 3, solver=h)

    # Create first mock connection (node as source)
    power_into_source_1 = h.addVariables(3, lb=-10, ub=10, name_prefix="conn1_into_source_", out_array=True)
    mock_conn1 = Mock(spec=Connection)
    mock_conn1.power_into_source = power_into_source_1

    # Create second mock connection (node as target)
    power_into_target_2 = h.addVariables(3, lb=-10, ub=10, name_prefix="conn2_into_target_", out_array=True)
    mock_conn2 = Mock(spec=Connection)
    mock_conn2.power_into_target = power_into_target_2

    # Register both connections
    node.register_connection(mock_conn1, "source")
    node.register_connection(mock_conn2, "target")

    # Call connection_power - should combine both connections
    result = node.connection_power()

    # Verify it's an array with 3 elements
    assert len(result) == 3

    # Set specific values and verify the combined calculation for period 2
    # conn1 (source): power_into_source = -1.6
    # conn2 (target): power_into_target = 4.64
    # Total net power: -1.6 + 4.64 = 3.04
    h.addConstr(power_into_source_1[2] == -1.6)
    h.addConstr(power_into_target_2[2] == 4.64)
    h.minimize(result[2])

    assert h.val(result[2]) == pytest.approx(3.04)


def test_element_default_outputs(solver: Highs) -> None:
    """Test Element base class default outputs() returns empty dict."""

    # Create a minimal Element subclass that doesn't override outputs()
    class MinimalElement(Element[str, str]):
        pass

    element = MinimalElement("test", [1.0], solver=solver)
    assert element.outputs() == {}
