"""Tests to improve coverage for element.py edge cases."""

from functools import reduce
import operator
from typing import Literal
from unittest.mock import Mock

from highspy import Highs, HighsModelStatus
from highspy.highs import HighspyArray
import numpy as np
import pytest

from custom_components.haeo.core.model.element import ELEMENT_POWER_BALANCE, Element, NetworkElement
from custom_components.haeo.core.model.elements.connection import Connection
from custom_components.haeo.core.model.elements.node import Node


@pytest.mark.parametrize(
    ("end", "attr"),
    [
        ("source", "power_into_source"),
        ("target", "power_into_target"),
    ],
    ids=["source", "target"],
)
def test_connection_power_by_end(solver: Highs, end: Literal["source", "target"], attr: str) -> None:
    """Connection power aggregates from the correct attribute for source/target ends."""
    node = Node(name="test_node", periods=np.array([1.0] * 3), solver=solver)
    power = solver.addVariables(3, lb=-10, ub=10, name_prefix=f"power_{end}_", out_array=True)

    mock_connection = Mock(spec=Connection)
    setattr(mock_connection, attr, power)
    node.register_connection(mock_connection, end)

    result = node.connection_power()
    solver.addConstr(power[0] == 7.5)
    solver.minimize(result[0])
    assert solver.val(result[0]) == pytest.approx(7.5)


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
    produced = node.element_power_produced()
    assert produced is not None
    solver.minimize(produced[0])
    assert solver.val(produced[0]) == pytest.approx(10.0, abs=0.01)


# ---------------------------------------------------------------------------
# #63 - Empty inbound/outbound forces consumption/production to zero
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("is_source", "is_sink", "tags_kwarg", "variable_attr"),
    [
        (False, True, {"inbound_tags": {99}}, "_consumed"),
        (True, False, {"outbound_tags": {99}}, "_produced"),
    ],
    ids=["empty-inbound-forces-consumption-zero", "empty-outbound-forces-production-zero"],
)
def test_empty_tag_overlap_forces_variable_to_zero(
    solver: Highs,
    is_source: bool,
    is_sink: bool,
    tags_kwarg: dict[str, set[int]],
    variable_attr: str,
) -> None:
    """When tag sets have no overlap with connection tags, the variable must be zero.

    If a node has inbound_tags/outbound_tags that don't overlap with any connection
    tag, the corresponding consumed/produced variable should be constrained to 0
    and the model should remain feasible (not unbounded).
    """
    n = 1
    node = Node(
        name="test",
        periods=np.array([1.0] * n),
        solver=solver,
        is_source=is_source,
        is_sink=is_sink,
        **tags_kwarg,
    )

    conn = _make_mock_connection(solver, n, {1}, "c1")
    end: Literal["source", "target"] = "target" if is_sink else "source"
    node.register_connection(conn, end)

    node.constraints()
    variable = getattr(node, variable_attr)
    solver.minimize(-variable[0])
    status = solver.getModelStatus()
    assert status == HighsModelStatus.kOptimal, f"Expected Optimal but got {solver.modelStatusToString(status)}"
    assert solver.val(variable[0]) == pytest.approx(0.0, abs=0.01)


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


# ---------------------------------------------------------------------------
# Untagged connection fallback (no tags on connections)
# ---------------------------------------------------------------------------


def test_untagged_connection_uses_simple_balance(solver: Highs) -> None:
    """When connections carry no tags, element_power_balance uses the simple path.

    The simple path is: connection_power() + produced - consumed == 0,
    without any per-tag decomposition.
    """
    n = 1
    # Source node with no tag configuration
    node = Node(
        name="src",
        periods=np.array([1.0] * n),
        solver=solver,
        is_source=True,
        is_sink=False,
    )

    # Mock connection with no tags (empty set)
    mock = Mock(spec=Connection)
    mock.connection_tags.return_value = set()
    power_into_source = solver.addVariables(n, lb=-100, ub=0, name_prefix="conn_src_", out_array=True)
    mock.power_into_source = power_into_source

    node.register_connection(mock, "source")

    node.constraints()

    # Force outflow of 5 kW and verify production matches
    solver.addConstr(power_into_source[0] == -5.0)
    produced = node.element_power_produced()
    assert produced is not None
    solver.minimize(produced[0])
    assert solver.val(produced[0]) == pytest.approx(5.0, abs=0.01)


def test_disconnected_element_returns_no_constraints(solver: Highs) -> None:
    """A network element with no connections and no production/consumption returns None.

    This exercises the early return in element_power_balance when there are no
    tags, no connections, and no external power.
    """

    class Passthrough(NetworkElement[str]):
        pass

    element = Passthrough(
        name="passthrough",
        periods=np.array([1.0]),
        solver=solver,
        output_names=frozenset(),
    )
    assert element.element_power_balance() is None


def test_passthrough_element_constrains_connection_to_zero(solver: Highs) -> None:
    """A passthrough element (no production/consumption) constrains its connection power to zero."""

    class Passthrough(NetworkElement[str]):
        pass

    n = 1
    element = Passthrough(
        name="passthrough",
        periods=np.array([1.0] * n),
        solver=solver,
        output_names=frozenset(),
    )

    mock = Mock(spec=Connection)
    mock.connection_tags.return_value = set()
    power = solver.addVariables(n, lb=-100, ub=100, name_prefix="conn_", out_array=True)
    mock.power_into_source = power
    element.register_connection(mock, "source")

    element.constraints()
    solver.minimize(-power[0])
    assert solver.val(power[0]) == pytest.approx(0.0, abs=0.01)


def test_blocked_tag_skips_connection_without_tag(solver: Highs) -> None:
    """Blocked-tag loop skips connections that don't carry the blocked tag.

    When a node blocks tag 2 but one connection only carries tag 1,
    the blocking loop should skip that connection entirely.
    """
    n = 1
    node = Node(
        name="hub",
        periods=np.array([1.0] * n),
        solver=solver,
        is_source=True,
        is_sink=True,
        outbound_tags={1},
        inbound_tags={1},
    )

    # conn1 carries tags {1, 2} — tag 2 must be blocked
    conn1 = _make_mock_connection(solver, n, {1, 2}, "c1")
    # conn2 carries only tag {1} — blocking loop for tag 2 should skip this
    conn2 = _make_mock_connection(solver, n, {1}, "c2")
    node.register_connection(conn1, "target")
    node.register_connection(conn2, "source")

    node.constraints()

    # Tag 2 flows on conn1 should be blocked
    tag2_in = conn1.power_into_target_for_tag(2)
    solver.minimize(-tag2_in[0])
    assert solver.val(tag2_in[0]) == pytest.approx(0.0, abs=0.01)
