"""Adapter-layer tests using element-specific test data modules."""

import pytest

from custom_components.haeo.elements import ElementConfigData, ElementConfigSchema
from tests.test_data.elements import ADAPTER_HELPERS, ALL_VALID, ElementValidCase

Case = ElementValidCase[ElementConfigSchema, ElementConfigData]


@pytest.mark.parametrize("case", ALL_VALID, ids=lambda case: case["element_type"])
def test_create_model_elements(case: Case) -> None:
    """Verify adapter transforms config into expected model elements."""

    helper = ADAPTER_HELPERS[case["element_type"]]
    result = helper.create_model_elements(case["data"])
    assert result == case["model"]


@pytest.mark.parametrize("case", ALL_VALID, ids=lambda case: case["element_type"])
def test_outputs_mapping(case: Case) -> None:
    """Verify adapter maps model outputs to device outputs."""

    helper = ADAPTER_HELPERS[case["element_type"]]
    result = helper.outputs(case["data"]["name"], case["model_outputs"])
    assert result == case["outputs"]
