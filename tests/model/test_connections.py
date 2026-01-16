"""Model connection output tests covering reporting and validation helpers."""

from highspy import Highs
from highspy.highs import highs_linear_expression, highs_var
import pytest

from typing import TypeGuard, cast

from custom_components.haeo.model.elements.connection import Connection
from custom_components.haeo.model.output_data import ModelOutputValue, OutputData

from . import test_data
from .test_data.connection_types import (
    ConnectionTestCase,
    ConnectionTestCaseInputs,
    ExpectedOutput,
    ExpectedOutputFixture,
    ExpectedOutputs,
)


def _serialize_output_value(output_value: ModelOutputValue) -> ExpectedOutputFixture:
    if isinstance(output_value, OutputData):
        if output_value.unit is None:
            msg = "Expected unit for connection output"
            raise ValueError(msg)
        output: ExpectedOutput = {
            "type": output_value.type,
            "unit": output_value.unit,
            "values": tuple(float(value) for value in output_value.values),
        }
        return output
    return {name: _serialize_output_value(child) for name, child in output_value.items()}


def _solve_connection_scenario(element: Connection[str], inputs: ConnectionTestCaseInputs | None) -> ExpectedOutputs:
    """Set up and solve an optimization scenario for a connection.

    Args:
        element: The connection to test (must have _solver set)
        inputs: Configuration dict with power values and parameters, or None for no optimization

    Returns:
        Dict mapping output names to {type, unit, values}

    """
    # Use the element's solver instance (set in constructor)
    h = element._solver

    # Always call constraints to set up constraints (variables already exist)
    element.constraints()

    if inputs is None:
        # No optimization - just solve with no objective and get outputs directly
        h.run()
        outputs = element.outputs()
        return {name: _serialize_output_value(output_data) for name, output_data in outputs.items()}

    # Get n_periods and periods from element
    n_periods = element.n_periods
    periods = element.periods

    source_power = inputs.get("source_power", [None] * n_periods)
    target_power = inputs.get("target_power", [None] * n_periods)
    source_cost = inputs.get("source_cost", 0.0)
    target_cost = inputs.get("target_cost", 0.0)

    # Create power variables: None = unbounded (free), float = fixed value
    # Note: HiGHS defaults to lb=0, so we must explicitly set lb=-inf for free variables
    neginf = float("-inf")
    source_vars: list[highs_var] = []
    target_vars: list[highs_var] = []

    for i, val in enumerate(source_power):
        if val is None:
            source_vars.append(h.addVariable(lb=neginf, name=f"source_power_{i}"))
        else:
            source_vars.append(h.addVariable(lb=val, ub=val, name=f"source_power_{i}"))

    for i, val in enumerate(target_power):
        if val is None:
            target_vars.append(h.addVariable(lb=neginf, name=f"target_power_{i}"))
        else:
            target_vars.append(h.addVariable(lb=val, ub=val, name=f"target_power_{i}"))

    # Power balance: net flow at each side
    for i in range(n_periods):
        h.addConstr(source_vars[i] == element.power_source_target[i] - element.power_target_source[i])
        h.addConstr(target_vars[i] == element.power_source_target[i] - element.power_target_source[i])

    # Apply constraints via reactive pattern
    element.constraints()

    # Collect cost from element (aggregates all @cost methods)
    element_cost = element.cost()
    cost_terms: list[highs_linear_expression] = []
    if element_cost is not None:
        cost_terms.append(element_cost)

    if source_cost != 0.0:
        cost_terms.append(Highs.qsum(source_vars[i] * source_cost * periods[i] for i in range(n_periods)))
    if target_cost != 0.0:
        cost_terms.append(Highs.qsum(target_vars[i] * target_cost * periods[i] for i in range(n_periods)))

    h.minimize(Highs.qsum(cost_terms))

    # Extract and return outputs
    outputs = element.outputs()
    return {name: _serialize_output_value(output_data) for name, output_data in outputs.items()}


def _is_expected_output(value: ExpectedOutputFixture) -> TypeGuard[ExpectedOutput]:
    return {"type", "unit", "values"}.issubset(value.keys())


def _assert_outputs_match(actual: ExpectedOutputFixture, expected: ExpectedOutputFixture) -> None:
    if _is_expected_output(expected):
        assert _is_expected_output(actual)
        assert actual["type"] == expected["type"]
        assert actual["unit"] == expected["unit"]
        assert actual["values"] == pytest.approx(expected["values"], rel=1e-9, abs=1e-9)
        return

    assert not _is_expected_output(actual)
    actual_map = cast(ExpectedOutputs, actual)
    expected_map = cast(ExpectedOutputs, expected)
    assert set(actual_map.keys()) == set(expected_map.keys())
    for output_name, expected_value in expected_map.items():
        _assert_outputs_match(actual_map[output_name], expected_value)


@pytest.mark.parametrize(
    "case",
    test_data.VALID_CONNECTION_CASES,
    ids=lambda case: case["description"].lower().replace(" ", "_"),
)
def test_connection_outputs(case: ConnectionTestCase, solver: Highs) -> None:
    """Connection.get_outputs should report expected series for each connection type."""

    # Create element using the factory with the solver
    factory = case["factory"]
    data = case["data"].copy()
    data["solver"] = solver
    element = factory(**data)
    assert isinstance(element, Connection)

    # Run optimization scenario (or get outputs directly if no inputs)
    outputs = _solve_connection_scenario(element, case.get("inputs"))

    # Validate outputs match expected
    assert "expected_outputs" in case
    expected_outputs = case["expected_outputs"]
    _assert_outputs_match(outputs, expected_outputs)


@pytest.mark.parametrize(
    "case",
    test_data.INVALID_CONNECTION_CASES,
    ids=lambda case: case["description"].lower().replace(" ", "_"),
)
def test_connection_validation(case: ConnectionTestCase, solver: Highs) -> None:
    """Connection classes should validate input sequence lengths match n_periods."""

    assert "expected_error" in case
    data = case["data"].copy()
    data["solver"] = solver
    with pytest.raises(ValueError, match=case["expected_error"]):
        case["factory"](**data)


def test_base_connection_power_into_properties(solver: Highs) -> None:
    """Base Connection class power_into_source and power_into_target properties."""
    # Create a base Connection (lossless bidirectional)
    conn: Connection[str] = Connection(
        name="test_conn",
        periods=[1.0, 1.0],
        solver=solver,
        source="source_element",
        target="target_element",
    )

    # Fix power values: 5 kW source->target in period 0, 3 kW target->source in period 1
    solver.addConstr(conn.power_source_target[0] == 5.0)
    solver.addConstr(conn.power_target_source[0] == 0.0)
    solver.addConstr(conn.power_source_target[1] == 0.0)
    solver.addConstr(conn.power_target_source[1] == 3.0)

    solver.run()

    # power_into_source = target->source minus source->target
    # Period 0: 0 - 5 = -5 (power flows out of source)
    # Period 1: 3 - 0 = 3 (power flows into source)
    power_into_source = [solver.val(conn.power_into_source[i]) for i in range(2)]
    assert power_into_source == pytest.approx([-5.0, 3.0])

    # power_into_target = source->target minus target->source
    # Period 0: 5 - 0 = 5 (power flows into target)
    # Period 1: 0 - 3 = -3 (power flows out of target)
    power_into_target = [solver.val(conn.power_into_target[i]) for i in range(2)]
    assert power_into_target == pytest.approx([5.0, -3.0])

    # Verify source and target properties
    assert conn.source == "source_element"
    assert conn.target == "target_element"
