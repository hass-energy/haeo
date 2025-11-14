"""Model element output tests covering reporting and validation helpers."""

from typing import Any

from pulp import LpMinimize, LpProblem, LpVariable, getSolver, lpSum
import pytest

from custom_components.haeo.model import extract_values
from custom_components.haeo.model.connection import Connection

from . import test_data


def _solve_element_scenario(element: Any, inputs: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Set up and solve an optimization scenario for an element.

    Args:
        element: The element to test
        inputs: Configuration dict with power values and parameters, or None for no optimization

    Returns:
        Dict mapping output names to {type, unit, values}

    """
    if inputs is None:
        # No optimization - get outputs directly
        outputs = element.get_outputs()
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

    problem = LpProblem(f"test_{element.name}", LpMinimize)  # type: ignore[no-untyped-call]

    # Add element constraints
    for constraint in element.constraints():
        problem += constraint

    # Handle Connection elements (two-sided power balance)
    if isinstance(element, Connection):
        source_power = inputs.get("source_power", [None] * n_periods)
        target_power = inputs.get("target_power", [None] * n_periods)
        source_cost = inputs.get("source_cost", 0.0)
        target_cost = inputs.get("target_cost", 0.0)

        # Create power variables: None = unbounded, float = fixed
        source_vars = [
            LpVariable(f"source_power_{i}") if val is None else float(val) for i, val in enumerate(source_power)
        ]
        target_vars = [
            LpVariable(f"target_power_{i}") if val is None else float(val) for i, val in enumerate(target_power)
        ]

        # Power balance: net flow at each side
        for i in range(n_periods):
            problem += source_vars[i] == element.power_source_target[i] - element.power_target_source[i]
            problem += target_vars[i] == element.power_source_target[i] - element.power_target_source[i]

        # Objective function
        objective = element.cost()
        if source_cost != 0.0:
            objective += lpSum(source_vars[i] * source_cost * period for i in range(n_periods))
        if target_cost != 0.0:
            objective += lpSum(target_vars[i] * target_cost * period for i in range(n_periods))
        problem += objective

    else:
        # Regular elements (Battery, Grid, PV, Load)
        power = inputs.get("power", [None] * n_periods)
        power_cost = inputs.get("cost", 0.0)

        # Create power variables
        power_vars = [LpVariable(f"power_{i}") if val is None else float(val) for i, val in enumerate(power)]

        # Get consumption and production (treat None as zero)
        consumption = getattr(element, "power_consumption", None) or [0.0] * n_periods
        production = getattr(element, "power_production", None) or [0.0] * n_periods

        # Power balance constraint (same for all elements)
        for i in range(n_periods):
            problem += power_vars[i] == consumption[i] - production[i]

        # Objective function
        objective = element.cost()
        if power_cost != 0.0:
            objective += lpSum(power_vars[i] * power_cost * period for i in range(n_periods))
        problem += objective

    # Solve
    solver = getSolver("HiGHS", msg=0)
    status = problem.solve(solver)  # type: ignore[no-untyped-call]
    if status != 1:
        msg = f"Optimization failed with status {status}"
        raise ValueError(msg)

    # Extract and return outputs
    outputs = element.get_outputs()
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
    test_data.VALID_CASES,
    ids=lambda case: case["description"].lower().replace(" ", "_"),
)
def test_element_outputs(case: dict[str, Any]) -> None:
    """Element.get_outputs should report expected series for each element type."""

    # Create element using the factory
    factory = case["factory"]
    data = case["data"].copy()
    element = factory(**data)

    # Run optimization scenario (or get outputs directly if no inputs)
    outputs = _solve_element_scenario(element, case.get("inputs"))

    # Validate outputs match expected
    expected_outputs = case["expected_outputs"]
    assert set(outputs.keys()) == set(expected_outputs.keys())

    for output_name, expected in expected_outputs.items():
        output = outputs[output_name]
        assert output["type"] == expected["type"]
        assert output["unit"] == expected["unit"]
        assert output["values"] == expected["values"]


@pytest.mark.parametrize(
    "case",
    test_data.INVALID_CASES,
    ids=lambda case: case["description"].lower().replace(" ", "_"),
)
def test_element_validation(case: dict[str, Any]) -> None:
    """Element classes should validate input sequence lengths match n_periods."""

    with pytest.raises(ValueError, match=case["expected_error"]):
        case["element_class"](**case["data"])


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
