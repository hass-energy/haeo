"""Tests to improve coverage for element.py edge cases."""

from functools import reduce
import operator
from unittest.mock import Mock

from highspy import Highs, HighsModelStatus
from highspy.highs import HighspyArray
import numpy as np
import pytest

from custom_components.haeo.core.model.element import ELEMENT_POWER_BALANCE, Element
from custom_components.haeo.core.model.elements.connection import Connection
from custom_components.haeo.core.model.elements.node import Node


def test_connection_power_with_target_end(solver: Highs) -> None:
    """Test connection_power when element is registered as target end of connection.

    The connection's power_into_target provides the net power flowing into the element.
    """
    h = solver

    # Create a simple node element
    node = Node(name="test_node", periods=np.array([1.0] * 3), solver=h)

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
    node = Node(name="test_node", periods=np.array([1.0] * 3), solver=h)

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


def test_constraints_populates_constraint_state(solver: Highs) -> None:
    """Test that constraints() applies constraints via @constraint decorators.

    With the reactive pattern, constraints are discovered via @constraint decorators
    and applied to the solver when constraints() is called.
    """
    h = solver

    # Create a simple element that has constraint methods
    # Use is_sink=False so the element_power_balance actually creates constraints
    element = Node(name="test_node", periods=np.array([1.0] * 3), solver=h, is_source=True, is_sink=False)

    # Call constraints to trigger decorator lifecycle
    constraints_dict = element.constraints()

    # After calling, constraint state should exist
    # Node has element_power_balance from Element base (creates constraints when not both source+sink)
    assert ELEMENT_POWER_BALANCE in constraints_dict
    assert constraints_dict[ELEMENT_POWER_BALANCE] is not None


def test_connection_power_with_multiple_connections(solver: Highs) -> None:
    """Test connection_power with multiple connections including both source and target ends.

    Total net power = sum of all connection power_into_* values.
    """
    h = solver

    # Create a simple node element
    node = Node(name="test_node", periods=np.array([1.0] * 3), solver=h)

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
    class MinimalElement(Element[str]):
        pass

    element = MinimalElement("test", np.array([1.0]), solver=solver, output_names=frozenset())
    assert element.outputs() == {}


# ---------------------------------------------------------------------------
# Helpers for tagged power balance tests
# ---------------------------------------------------------------------------


def _make_mock_connection(
    solver: Highs,
    n_periods: int,
    tags: set[int],
    name: str,
) -> Mock:
    """Create a mock connection with per-tag LP variables."""
    mock = Mock(spec=Connection)
    mock.connection_tags.return_value = tags

    power_in: dict[int, HighspyArray] = {}
    power_out: dict[int, HighspyArray] = {}
    for tag in tags:
        p_in = solver.addVariables(n_periods, lb=0, ub=100, name_prefix=f"{name}_pin{tag}_", out_array=True)
        p_out = solver.addVariables(n_periods, lb=0, ub=100, name_prefix=f"{name}_pout{tag}_", out_array=True)
        power_in[tag] = p_in
        power_out[tag] = p_out
        # Efficiency 1:1 for simplicity
        solver.addConstrs(p_out == p_in)

    mock.power_into_source_for_tag = Mock(side_effect=lambda t: -power_in[t])
    mock.power_into_target_for_tag = Mock(side_effect=lambda t: power_out[t])
    mock.power_into_source = -reduce(operator.add, power_in.values())
    mock.power_into_target = reduce(operator.add, power_out.values())

    return mock


# ---------------------------------------------------------------------------
# #66 - Production duplication on multi-tag outbound
# ---------------------------------------------------------------------------


def test_multi_tag_outbound_does_not_duplicate_production(solver: Highs) -> None:
    """Production should be decomposed across outbound tags, not duplicated.

    When a source element has outbound_tags={1, 2} and produces 10 kW,
    the total production across all tags must sum to 10 kW, not 10 kW per tag.
    """
    n = 1
    # Source node with multi-tag outbound, no consumption
    node = Node(
        name="src",
        periods=np.array([1.0] * n),
        solver=solver,
        is_source=True,
        is_sink=False,
        outbound_tags={1, 2},
    )

    # Two connections, one per tag
    conn1 = _make_mock_connection(solver, n, {1}, "c1")
    conn2 = _make_mock_connection(solver, n, {2}, "c2")
    node.register_connection(conn1, "source")
    node.register_connection(conn2, "source")

    # Apply constraints and optimize: minimize production cost
    node.constraints()
    # Force total outflow = 10 kW via connections
    solver.addConstr(-conn1.power_into_source_for_tag(1)[0] + (-conn2.power_into_source_for_tag(2)[0]) == 10)
    solver.minimize(node._produced[0])
    assert solver.val(node._produced[0]) == pytest.approx(10.0, abs=0.01)


# ---------------------------------------------------------------------------
# #63 - Empty inbound leaves consumption unconstrained
# ---------------------------------------------------------------------------


def test_empty_inbound_forces_consumption_to_zero(solver: Highs) -> None:
    """When inbound_tags has no overlap with connection tags, consumption must be zero.

    If a sink element has inbound_tags={99} but all connections carry tag {1},
    the element cannot consume any power. Even when the optimizer has incentive
    to consume (negative cost), consumption should be constrained to 0 and the
    model should remain feasible (not unbounded).
    """
    n = 1
    # Sink node that can only consume tag 99
    node = Node(
        name="sink",
        periods=np.array([1.0] * n),
        solver=solver,
        is_source=False,
        is_sink=True,
        inbound_tags={99},
    )

    # Connection carries tag 1 (no overlap with inbound_tags={99})
    conn = _make_mock_connection(solver, n, {1}, "c1")
    node.register_connection(conn, "target")

    node.constraints()
    # Give incentive to consume: minimize -consumed (i.e. maximize consumption)
    # If consumption is properly constrained, it should be 0 and model should be optimal
    solver.minimize(-node._consumed[0])
    status = solver.getModelStatus()
    assert status == HighsModelStatus.kOptimal, f"Expected Optimal but got {solver.modelStatusToString(status)}"
    assert solver.val(node._consumed[0]) == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# #61 - Per-connection tag blocking (not just net-zero)
# ---------------------------------------------------------------------------


def test_blocked_tag_forces_per_connection_flow_to_zero(solver: Highs) -> None:
    """Tags outside outbound/inbound must have zero flow per-connection, not just net-zero.

    If a node has outbound_tags={1} and inbound_tags={1}, tag 2 should be
    fully blocked — no flow on any connection for tag 2, not just net zero.
    """
    n = 1
    # Node that only allows tag 1
    node = Node(
        name="hub",
        periods=np.array([1.0] * n),
        solver=solver,
        is_source=True,
        is_sink=True,
        outbound_tags={1},
        inbound_tags={1},
    )

    # Two connections, both carry tags {1, 2}
    conn_in = _make_mock_connection(solver, n, {1, 2}, "cin")
    conn_out = _make_mock_connection(solver, n, {1, 2}, "cout")
    node.register_connection(conn_in, "target")
    node.register_connection(conn_out, "source")

    node.constraints()

    # Try to push tag-2 power through: conn_in feeds 5 kW tag-2 in,
    # conn_out sends 5 kW tag-2 out. Net zero at node, but should be blocked.
    # We maximize tag-2 inflow on conn_in; if blocking works, it should be 0.
    tag2_in = conn_in.power_into_target_for_tag(2)
    solver.minimize(-tag2_in[0])

    assert solver.val(tag2_in[0]) == pytest.approx(0.0, abs=0.01)
