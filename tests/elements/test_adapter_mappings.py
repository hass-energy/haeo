"""Adapter-layer tests using element-specific test data modules."""

import pytest

from custom_components.haeo.elements import ELEMENT_TYPES, ElementConfigData, ElementConfigSchema, ElementType
from tests.test_data.elements import VALID_CONFIGS_BY_TYPE, ElementValidCase


def _all_valid_cases() -> list[tuple[ElementType, ElementValidCase[ElementConfigSchema, ElementConfigData]]]:
    return [(element_type, case) for element_type, configs in VALID_CONFIGS_BY_TYPE.items() for case in configs]


def _valid_case_id(param: object) -> str:
    if isinstance(param, tuple) and len(param) >= 2 and isinstance(param[1], dict):
        description = param[1].get("description") or param[1].get("element_type")
        if isinstance(description, str):
            return description
    return str(param)


@pytest.mark.parametrize(("element_type", "case"), _all_valid_cases(), ids=_valid_case_id)
def test_create_model_elements(
    element_type: ElementType, case: ElementValidCase[ElementConfigSchema, ElementConfigData]
) -> None:
    """Verify adapter transforms config into expected model elements."""

    entry = ELEMENT_TYPES[element_type]
    result = entry.create_model_elements(case["data"])
    assert result == case["model"]


@pytest.mark.parametrize(("element_type", "case"), _all_valid_cases(), ids=_valid_case_id)
def test_updates_mapping(
    element_type: ElementType, case: ElementValidCase[ElementConfigSchema, ElementConfigData]
) -> None:
    """Verify adapter maps model outputs to device sensor states."""

    entry = ELEMENT_TYPES[element_type]
    result = entry.updates(case["data"]["name"], case["model_outputs"], case["data"])
    assert result == case["outputs"]
