"""Model element output tests covering reporting and validation helpers."""

from typing import Any

from pulp import LpAffineExpression, LpMinimize, LpProblem, LpVariable, getSolver, lpSum
import pytest

from custom_components.haeo.model.util import broadcast_to_sequence, extract_values

from . import test_data
from .test_data.element_types import ElementTestCase, ElementTestCaseInputs


def _solve_element_scenario(element: Any, inputs: ElementTestCaseInputs | None) -> dict[str, dict[str, Any]]:
    """Set up and solve an optimization scenario for an element.

    Args:
        element: The element to test
        inputs: Configuration dict with power values and parameters, or None for no optimization

    Returns:
        Dict mapping output names to {type, unit, values}

    """
    if inputs is not None:
        # Get n_periods and period from element
        n_periods = element.n_periods
        period = element.period

        problem = LpProblem(f"test_{element.name}", LpMinimize)

        # Regular elements (Battery, Grid, PV, Load)
        power = inputs.get("power", [None] * n_periods)

        # Create the variables to inject power
        power_inputs = [
            LpVariable(f"test_in_{i}", lowBound=0.0) if val is None else LpAffineExpression(constant=max(val, 0.0))
            for i, val in enumerate(power)
        ]
        power_outputs = [
            LpVariable(f"test_out_{i}", lowBound=0.0) if val is None else LpAffineExpression(constant=max(-val, 0.0))
            for i, val in enumerate(power)
        ]
        total_power = [power_inputs[i] - power_outputs[i] for i in range(n_periods)]

        # Mock connection_power() to return the power variables
        # This allows elements to set up their own internal power balance constraints
        def mock_connection_power(t: int) -> LpAffineExpression:
            return total_power[t]

        element.connection_power = mock_connection_power

        # Call build_constraints() to set up power balance with mocked connection_power
        element.build_constraints()

        # Add all element constraints (including the power balance from build_constraints)
        for constraint in element.constraints():
            problem += constraint

        # Add costs for the injected power
        input_cost = broadcast_to_sequence(inputs.get("input_cost", 0.0), n_periods)
        output_cost = broadcast_to_sequence(inputs.get("output_cost", 0.0), n_periods)

        # Objective function
        cost_terms = [
            *element.cost(),
            *[input_cost[i] * power_inputs[i] * period for i in range(n_periods) if input_cost[i] != 0.0],
            *[output_cost[i] * power_outputs[i] * period for i in range(n_periods) if output_cost[i] != 0.0],
        ]

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
    test_data.VALID_ELEMENT_CASES,
    ids=lambda case: case["description"].lower().replace(" ", "_"),
)
def test_element_outputs(case: ElementTestCase) -> None:
    """Element.get_outputs should report expected series for each element type."""

    # Create element using the factory
    factory = case["factory"]
    data = case["data"].copy()
    element = factory(**data)

    # Run optimization scenario (or get outputs directly if no inputs)
    outputs = _solve_element_scenario(element, case.get("inputs"))

    # Validate outputs match expected
    assert "expected_outputs" in case
    expected_outputs = case["expected_outputs"]
    assert set(outputs.keys()) == set(expected_outputs.keys())

    for output_name, expected in expected_outputs.items():
        output = outputs[output_name]
        assert output["type"] == expected["type"]
        assert output["unit"] == expected["unit"]
        assert output["values"] == pytest.approx(expected["values"], rel=1e-9, abs=1e-9)


@pytest.mark.parametrize(
    "case",
    test_data.INVALID_ELEMENT_CASES,
    ids=lambda case: case["description"].lower().replace(" ", "_"),
)
def test_element_validation(case: ElementTestCase) -> None:
    """Element classes should validate input sequence lengths match n_periods."""

    assert "expected_error" in case
    with pytest.raises(ValueError, match=case["expected_error"]):
        case["factory"](**case["data"])


def test_extract_values_converts_lp_variables() -> None:
    """extract_values should coerce PuLP variables to floats."""

    sequence = test_data.lp_sequence("test", 3)
    result = extract_values(sequence)

    assert isinstance(result, tuple)
    assert len(result) == 3
    assert all(isinstance(value, float) for value in result)


def test_extract_values_handles_none() -> None:
    """extract_values should return empty tuple for None input."""

    result = extract_values(None)

    assert isinstance(result, tuple)
    assert len(result) == 0
