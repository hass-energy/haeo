"""Model element output tests covering reporting and validation helpers."""

from typing import Any

from highspy import Highs
from highspy.highs import HighspyArray
import numpy as np
import pytest

from custom_components.haeo.core.model.elements.node import Node
from custom_components.haeo.core.model.tests import test_data
from custom_components.haeo.core.model.tests.test_data.element_types import ElementTestCase, ElementTestCaseInputs
from custom_components.haeo.core.model.util import broadcast_to_sequence


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

        # Create HighspyArray variables to inject power
        power_in_vars = h.addVariables(n_periods, lb=0.0, name_prefix="test_in_", out_array=True)
        power_out_vars = h.addVariables(n_periods, lb=0.0, name_prefix="test_out_", out_array=True)

        # For fixed values, add constraints to fix the variables
        for i, val in enumerate(power):
            if val is not None:
                # Fixed value - constrain the variables
                h.addConstr(power_in_vars[i] == max(val, 0.0))
                h.addConstr(power_out_vars[i] == max(-val, 0.0))

        # Total power as HighspyArray
        total_power = power_in_vars - power_out_vars

        # Mock connection_power() to return the power array for all periods
        # This allows elements to set up their own internal power balance constraints
        def mock_connection_power() -> HighspyArray:
            return total_power

        element.connection_power = mock_connection_power

        # Call constraints() to set up power balance with mocked connection_power
        element.constraints()

        # Collect cost from element (aggregates all @cost methods)
        element_costs: list[Any] = []
        if (element_cost := element.cost()) is not None:
            element_costs.append(element_cost)

        input_cost = broadcast_to_sequence(inputs.get("input_cost", 0.0), n_periods)
        output_cost = broadcast_to_sequence(inputs.get("output_cost", 0.0), n_periods)

        cost_terms = [
            *element_costs,
            *[input_cost[i] * power_in_vars[i] * periods[i] for i in range(n_periods) if input_cost[i] != 0.0],
            *[output_cost[i] * power_out_vars[i] * periods[i] for i in range(n_periods) if output_cost[i] != 0.0],
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
    """Element.extract_values should coerce HiGHS variables to floats."""
    h = Highs()
    output_off = False
    h.setOptionValue("output_flag", output_off)

    variables, h = test_data.highs_sequence(h, "test", 3)

    # Create a simple element to test extract_values
    element = Node(name="test", periods=np.array([1.0, 1.0, 1.0]), solver=h)
    result = element.extract_values(variables)

    assert isinstance(result, tuple)
    assert len(result) == 3
    assert all(isinstance(value, float) for value in result)
    # Values should be 1.0, 2.0, 3.0 (set in highs_sequence)
    assert result == pytest.approx((1.0, 2.0, 3.0))


def test_extract_values_handles_none() -> None:
    """Element.extract_values should return empty tuple for None input."""
    h = Highs()
    element = Node(name="test", periods=np.array([1.0]), solver=h)
    result = element.extract_values(None)

    assert isinstance(result, tuple)
    assert len(result) == 0
