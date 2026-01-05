"""Model connection output tests covering reporting and validation helpers."""

from typing import Any

from highspy import Highs
from highspy.highs import highs_linear_expression, highs_var
import pytest

from custom_components.haeo.model.elements.connection import Connection
from custom_components.haeo.model.elements.power_connection import PowerConnection

from . import test_data
from .test_data.connection_types import ConnectionTestCase, ConnectionTestCaseInputs


def _solve_connection_scenario(
    element: PowerConnection, inputs: ConnectionTestCaseInputs | None
) -> dict[str, dict[str, Any]]:
    """Set up and solve an optimization scenario for a connection.

    Args:
        element: The connection to test (must have _solver set)
        inputs: Configuration dict with power values and parameters, or None for no optimization

    Returns:
        Dict mapping output names to {type, unit, values}

    """
    # Use the element's solver instance (set in constructor)
    h = element._solver

    # Always call apply_constraints to set up constraints (variables already exist)
    element.apply_constraints()

    if inputs is None:
        # No optimization - just solve with no objective and get outputs directly
        h.run()
        outputs = element.outputs()
        return {
            name: {
                "type": output_data.type,
                "unit": output_data.unit,
                "values": output_data.values,
            }
            for name, output_data in outputs.items()
        }

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

    # Apply constraints and costs via reactive pattern
    element.apply_constraints()
    element.apply_costs()

    # Objective function - collect costs from _applied_costs (flatten lists)
    cost_terms: list[highs_linear_expression] = []
    for cost_value in element._applied_costs.values():
        if cost_value is not None:
            if isinstance(cost_value, list):
                cost_terms.extend(cost_value)
            else:
                cost_terms.append(cost_value)
    if source_cost != 0.0:
        cost_terms.append(Highs.qsum(source_vars[i] * source_cost * periods[i] for i in range(n_periods)))
    if target_cost != 0.0:
        cost_terms.append(Highs.qsum(target_vars[i] * target_cost * periods[i] for i in range(n_periods)))

    h.minimize(Highs.qsum(cost_terms))

    # Extract and return outputs
    outputs = element.outputs()
    return {
        name: {
            "type": output_data.type,
            "unit": output_data.unit,
            "values": output_data.values,
        }
        for name, output_data in outputs.items()
    }


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

    # Run optimization scenario (or get outputs directly if no inputs)
    outputs = _solve_connection_scenario(element, case.get("inputs"))

    # Validate outputs match expected
    expected_outputs = case.get("expected_outputs")
    assert expected_outputs is not None
    assert set(outputs.keys()) == set(expected_outputs.keys())

    for output_name, expected in expected_outputs.items():
        output = outputs[output_name]
        assert output["type"] == expected["type"]
        assert output["unit"] == expected["unit"]
        assert output["values"] == pytest.approx(expected["values"], rel=1e-9, abs=1e-9)


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
