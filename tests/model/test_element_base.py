"""Tests to improve coverage for element.py edge cases."""

from unittest.mock import Mock

from highspy import Highs
import numpy as np
import pytest

from custom_components.haeo.model.connection import Connection
from custom_components.haeo.model.element import Element
from custom_components.haeo.model.node import Node


def test_connection_power_with_target_end(solver: Highs) -> None:
    """Test connection_power when element is registered as target end of connection.

    As target: power_in = power_st * eff_st, power_out = -power_ts
    Net power = power_st * eff_st - power_ts
    """
    h = solver

    # Create a simple node element
    node = Node(name="test_node", periods=[1.0] * 3, solver=h)

    # Create a mock connection with HiGHS variable arrays
    mock_connection = Mock(spec=Connection)
    mock_connection.power_source_target = h.addVariables(3, lb=0, ub=10, name_prefix="power_st_", out_array=True)
    mock_connection.power_target_source = h.addVariables(3, lb=0, ub=10, name_prefix="power_ts_", out_array=True)
    mock_connection.efficiency_source_target = np.array([0.95, 0.90, 0.85])
    mock_connection.efficiency_target_source = np.array([0.80, 0.75, 0.70])

    # Register the connection with node as TARGET
    node.register_connection(mock_connection, "target")

    # Call connection_power - should return array for all periods
    result = node.connection_power()

    # Verify it's an array with 3 elements
    assert len(result) == 3

    # Set specific values and verify the calculation
    # For target: net = power_st * eff_st - power_ts
    h.addConstr(mock_connection.power_source_target[0] == 10.0)
    h.addConstr(mock_connection.power_target_source[0] == 2.0)
    h.minimize(result[0])  # Minimize to get the value

    # Expected: 10 * 0.95 - 2 = 9.5 - 2 = 7.5
    assert h.val(result[0]) == pytest.approx(7.5)


def test_connection_power_with_source_end(solver: Highs) -> None:
    """Test connection_power when element is registered as source end of connection.

    As source: power_out = -power_st, power_in = power_ts * eff_ts
    Net power = -power_st + power_ts * eff_ts
    """
    h = solver

    # Create a simple node element
    node = Node(name="test_node", periods=[1.0] * 3, solver=h)

    # Create a mock connection with HiGHS variable arrays
    mock_connection = Mock(spec=Connection)
    mock_connection.power_source_target = h.addVariables(3, lb=0, ub=10, name_prefix="power_st_", out_array=True)
    mock_connection.power_target_source = h.addVariables(3, lb=0, ub=10, name_prefix="power_ts_", out_array=True)
    mock_connection.efficiency_source_target = np.array([0.95, 0.90, 0.85])
    mock_connection.efficiency_target_source = np.array([0.80, 0.75, 0.70])

    # Register the connection with node as SOURCE
    node.register_connection(mock_connection, "source")

    # Call connection_power - should return array for all periods
    result = node.connection_power()

    # Verify it's an array with 3 elements
    assert len(result) == 3

    # Set specific values and verify the calculation
    # For source: net = -power_st + power_ts * eff_ts
    h.addConstr(mock_connection.power_source_target[1] == 5.0)
    h.addConstr(mock_connection.power_target_source[1] == 4.0)
    h.minimize(result[1])  # Minimize to get the value

    # Expected: -5 + 4 * 0.75 = -5 + 3 = -2
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

    Total net power = sum of all connection powers
    conn1 (source): -power_st1 + power_ts1 * eff_ts1
    conn2 (target): power_st2 * eff_st2 - power_ts2
    """
    h = solver

    # Create a simple node element
    node = Node(name="test_node", periods=[1.0] * 3, solver=h)

    # Create first mock connection (node as source)
    mock_conn1 = Mock(spec=Connection)
    mock_conn1.power_source_target = h.addVariables(3, lb=0, ub=10, name_prefix="conn1_st_", out_array=True)
    mock_conn1.power_target_source = h.addVariables(3, lb=0, ub=10, name_prefix="conn1_ts_", out_array=True)
    mock_conn1.efficiency_source_target = np.array([0.95, 0.90, 0.85])
    mock_conn1.efficiency_target_source = np.array([0.80, 0.75, 0.70])

    # Create second mock connection (node as target)
    mock_conn2 = Mock(spec=Connection)
    mock_conn2.power_source_target = h.addVariables(3, lb=0, ub=10, name_prefix="conn2_st_", out_array=True)
    mock_conn2.power_target_source = h.addVariables(3, lb=0, ub=10, name_prefix="conn2_ts_", out_array=True)
    mock_conn2.efficiency_source_target = np.array([0.98, 0.96, 0.94])
    mock_conn2.efficiency_target_source = np.array([0.92, 0.88, 0.84])

    # Register both connections
    node.register_connection(mock_conn1, "source")
    node.register_connection(mock_conn2, "target")

    # Call connection_power - should combine both connections
    result = node.connection_power()

    # Verify it's an array with 3 elements
    assert len(result) == 3

    # Set specific values and verify the combined calculation for period 2
    # Expected calculation:
    #   conn1 (source): -power_st1 + power_ts1 * eff_ts1 = -3 + 2 * 0.70 = -1.6
    #   conn2 (target): power_st2 * eff_st2 - power_ts2 = 6 * 0.94 - 1 = 4.64
    #   Total net power: -1.6 + 4.64 = 3.04
    h.addConstr(mock_conn1.power_source_target[2] == 3.0)
    h.addConstr(mock_conn1.power_target_source[2] == 2.0)
    h.addConstr(mock_conn2.power_source_target[2] == 6.0)
    h.addConstr(mock_conn2.power_target_source[2] == 1.0)
    h.minimize(result[2])

    assert h.val(result[2]) == pytest.approx(3.04)


def test_element_default_outputs(solver: Highs) -> None:
    """Test Element base class default outputs() returns empty dict."""

    # Create a minimal Element subclass that doesn't override outputs()
    class MinimalElement(Element[str, str]):
        pass

    element = MinimalElement("test", [1.0], solver=solver)
    assert element.outputs() == {}
