"""Model element output tests covering reporting and validation helpers."""

from typing import Any

from highspy import Highs
from highspy.highs import highs_linear_expression
import pytest

from custom_components.haeo.model.util import broadcast_to_sequence, extract_values

from . import test_data
from .test_data.element_types import ElementTestCase, ElementTestCaseInputs


def _solve_element_scenario(element: Any, inputs: ElementTestCaseInputs | None) -> dict[str, dict[str, Any]]:
    """Set up and solve an optimization scenario for an element.

    Args:
        element: The element to test (must have _solver set)
        inputs: Configuration dict with power values and parameters, or None for no optimization

    Returns:
        Dict mapping output names to {type, unit, values}

    """
    if inputs is not None:
        # Get n_periods and periods from element
        n_periods = element.n_periods
        periods = element.periods

        # Use the element's solver instance (set in constructor)
        h = element._solver

        # Regular elements (Battery, Grid, PV, Load)
        power = inputs.get("power", [None] * n_periods)

        # Create the variables to inject power
        # For fixed values, use constant expressions (like PuLP's LpAffineExpression(constant=...))
        # rather than fixed-bound variables, to match original behavior
        power_inputs: list[highs_linear_expression] = []
        power_outputs: list[highs_linear_expression] = []

        for i, val in enumerate(power):
            if val is None:
                power_inputs.append(h.addVariable(lb=0.0, name=f"test_in_{i}"))
                power_outputs.append(h.addVariable(lb=0.0, name=f"test_out_{i}"))
            else:
                # Fixed value - use constant expression (not fixed-bound variable)
                power_inputs.append(highs_linear_expression(max(val, 0.0)))
                power_outputs.append(highs_linear_expression(max(-val, 0.0)))

        total_power = [power_inputs[i] - power_outputs[i] for i in range(n_periods)]

        # Mock connection_power() to return the power variables
        # This allows elements to set up their own internal power balance constraints
        def mock_connection_power(t: int) -> highs_linear_expression:
            return total_power[t]

        element.connection_power = mock_connection_power

        # Call build_constraints() to set up power balance with mocked connection_power
        element.build_constraints()

        # Collect all cost terms
        input_cost = broadcast_to_sequence(inputs.get("input_cost", 0.0), n_periods)
        output_cost = broadcast_to_sequence(inputs.get("output_cost", 0.0), n_periods)

        cost_terms = [
            *element.cost(),
            *[input_cost[i] * power_inputs[i] * periods[i] for i in range(n_periods) if input_cost[i] != 0.0],
            *[output_cost[i] * power_outputs[i] * periods[i] for i in range(n_periods) if output_cost[i] != 0.0],
        ]

        # Minimize
        if cost_terms:
            h.minimize(Highs.qsum(cost_terms))
        else:
            h.run()

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
def test_element_outputs(case: ElementTestCase, solver: Highs) -> None:
    """Element.get_outputs should report expected series for each element type."""

    # Create element using the factory with the solver
    factory = case["factory"]
    data = case["data"].copy()
    data["solver"] = solver
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

        # For shadow prices, compare absolute values to handle solver-dependent sign conventions
        # and dual degeneracy (different solvers may distribute duals across binding constraints)
        if output["type"] == "shadow_price":
            actual_abs = tuple(abs(v) for v in output["values"])
            expected_abs = tuple(abs(v) for v in expected["values"])
            assert actual_abs == pytest.approx(expected_abs, rel=1e-6, abs=1e-6), (
                f"{output_name}: absolute values differ\n"
                f"  actual:   {output['values']}\n"
                f"  expected: {expected['values']}"
            )
        else:
            assert output["values"] == pytest.approx(expected["values"], rel=1e-9, abs=1e-9)


@pytest.mark.parametrize(
    "case",
    test_data.INVALID_ELEMENT_CASES,
    ids=lambda case: case["description"].lower().replace(" ", "_"),
)
def test_element_validation(case: ElementTestCase, solver: Highs) -> None:
    """Element classes should validate input sequence lengths match n_periods."""

    assert "expected_error" in case
    data = case["data"].copy()
    data["solver"] = solver
    with pytest.raises(ValueError, match=case["expected_error"]):
        case["factory"](**data)


def test_extract_values_converts_highs_variables() -> None:
    """extract_values should coerce HiGHS variables to floats."""
    h = Highs()
    output_off = False
    h.setOptionValue("output_flag", output_off)

    variables, h = test_data.highs_sequence(h, "test", 3)
    result = extract_values(variables, h)

    assert isinstance(result, tuple)
    assert len(result) == 3
    assert all(isinstance(value, float) for value in result)
    # Values should be 1.0, 2.0, 3.0 (set in highs_sequence)
    assert result == pytest.approx((1.0, 2.0, 3.0))


def test_extract_values_handles_none() -> None:
    """extract_values should return empty tuple for None input."""

    result = extract_values(None)

    assert isinstance(result, tuple)
    assert len(result) == 0
