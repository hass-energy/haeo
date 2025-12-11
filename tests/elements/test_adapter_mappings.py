"""Adapter-layer tests using element-specific test data modules."""

from typing import Any

import pytest

from custom_components.haeo.elements import ELEMENT_TYPES, ElementConfigData, ElementConfigSchema, ElementType
from tests.test_data.elements import INVALID_MODEL_PARAMS_BY_TYPE, VALID_CONFIGS_BY_TYPE, ElementValidCase
from tests.test_data.elements.types import InvalidModelCase


def _all_valid_cases() -> list[tuple[ElementType, ElementValidCase[ElementConfigSchema, ElementConfigData]]]:
    return [(element_type, case) for element_type, configs in VALID_CONFIGS_BY_TYPE.items() for case in configs]


def _all_invalid_model_params() -> list[tuple[ElementType, InvalidModelCase[Any]]]:
    return [
        (element_type, param_case)
        for element_type, params_list in INVALID_MODEL_PARAMS_BY_TYPE.items()
        for param_case in params_list
    ]


@pytest.mark.parametrize(("element_type", "case"), _all_valid_cases(), ids=lambda c: c[1]["element_type"])
def test_create_model_elements(
    element_type: ElementType, case: ElementValidCase[ElementConfigSchema, ElementConfigData]
) -> None:
    """Verify adapter transforms config into expected model elements."""

    entry = ELEMENT_TYPES[element_type]
    result = entry.create_model_elements(case["data"])
    assert result == case["model"]


@pytest.mark.parametrize(("element_type", "case"), _all_valid_cases(), ids=lambda c: c[1]["element_type"])
def test_outputs_mapping(
    element_type: ElementType, case: ElementValidCase[ElementConfigSchema, ElementConfigData]
) -> None:
    """Verify adapter maps model outputs to device outputs."""

    entry = ELEMENT_TYPES[element_type]
    result = entry.outputs(case["data"]["name"], case["model_outputs"])
    assert result == case["outputs"]


@pytest.mark.parametrize(("element_type", "case"), _all_invalid_model_params(), ids=lambda c: c[0])
def test_invalid_model_params(element_type: ElementType, case: InvalidModelCase[Any]) -> None:
    """Ensure invalid model params raise ValueError for each element type."""

    entry = ELEMENT_TYPES[element_type]
    with pytest.raises(ValueError, match="charge"):
        entry.create_model_elements(case["params"])
