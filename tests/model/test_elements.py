"""Model element output tests covering reporting and validation helpers."""

from typing import Any

import pytest

from custom_components.haeo.model import extract_values

from . import test_data


@pytest.mark.parametrize(
    "case",
    test_data.VALID_CASES,
    ids=lambda case: case["description"].lower().replace(" ", "_"),
)
def test_element_outputs(case: dict[str, Any]) -> None:
    """Element.get_outputs should report expected series for each element type."""

    # Create element using the factory from the case
    element = case["factory"](case["data"])
    outputs = element.get_outputs()

    # Get expected outputs from the case
    expected_outputs = case["expected_outputs"]

    # Check we have exactly the expected output keys
    assert set(outputs.keys()) == set(expected_outputs.keys())

    # Validate each output
    for output_name, expected in expected_outputs.items():
        output = outputs[output_name]

        # Check type
        assert output.type == expected["type"], f"{output_name}: expected type {expected['type']}, got {output.type}"

        # Check unit
        assert output.unit == expected["unit"], f"{output_name}: expected unit {expected['unit']}, got {output.unit}"

        # Check values
        assert output.values == expected["values"], (
            f"{output_name}: expected values {expected['values']}, got {output.values}"
        )


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
