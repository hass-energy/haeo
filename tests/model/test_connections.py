"""Model connection output tests covering reporting and validation helpers."""

from typing import Any

from pulp import LpAffineExpression, LpMinimize, LpProblem, LpVariable, getSolver, lpSum
import pytest

from custom_components.haeo.model.connection import Connection

from . import test_data
from .test_data.connection_types import ConnectionTestCase, ConnectionTestCaseInputs


def _solve_connection_scenario(
    element: Connection, inputs: ConnectionTestCaseInputs | None
) -> dict[str, dict[str, Any]]:
    """Set up and solve an optimization scenario for a connection.

    Args:
        element: The connection to test
        inputs: Configuration dict with power values and parameters, or None for no optimization

    Returns:
        Dict mapping output names to {type, unit, values}

    """
    if inputs is None:
        # No optimization - get outputs directly
        outputs = element.outputs()
        return {
            name: {
                "type": output_data.type,
                "unit": output_data.unit,
                "values": output_data.values,
            }
            for name, output_data in outputs.items()
        }

    # Get n_periods and period from element
    n_periods = element.n_periods
    period = element.period

    problem = LpProblem(f"test_{element.name}", LpMinimize)

    # Add element constraints
    for constraint in element.constraints():
        problem += constraint

    source_power = inputs.get("source_power", [None] * n_periods)
    target_power = inputs.get("target_power", [None] * n_periods)
    source_cost = inputs.get("source_cost", 0.0)
    target_cost = inputs.get("target_cost", 0.0)

    # Create power variables: None = unbounded, float = fixed value as LpAffineExpression
    source_vars = [
        LpVariable(f"source_power_{i}") if val is None else LpAffineExpression(constant=val)
        for i, val in enumerate(source_power)
    ]
    target_vars = [
        LpVariable(f"target_power_{i}") if val is None else LpAffineExpression(constant=val)
        for i, val in enumerate(target_power)
    ]

    # Power balance: net flow at each side
    for i in range(n_periods):
        problem += source_vars[i] == element.power_source_target[i] - element.power_target_source[i]
        problem += target_vars[i] == element.power_source_target[i] - element.power_target_source[i]

    # Objective function
    cost_terms = list(element.cost())
    if source_cost != 0.0:
        cost_terms.append(lpSum(source_vars[i] * source_cost * period for i in range(n_periods)))
    if target_cost != 0.0:
        cost_terms.append(lpSum(target_vars[i] * target_cost * period for i in range(n_periods)))
    problem += lpSum(cost_terms)

    # Solve
    solver = getSolver("HiGHS", msg=0)
    status = problem.solve(solver)
    if status != 1:
        msg = f"Optimization failed with status {status}"
        raise ValueError(msg)

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
def test_connection_outputs(case: ConnectionTestCase) -> None:
    """Connection.get_outputs should report expected series for each connection type."""

    # Create element using the factory
    factory = case["factory"]
    data = case["data"].copy()
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
def test_connection_validation(case: ConnectionTestCase) -> None:
    """Connection classes should validate input sequence lengths match n_periods."""

    assert "expected_error" in case
    with pytest.raises(ValueError, match=case["expected_error"]):
        case["factory"](**case["data"])
