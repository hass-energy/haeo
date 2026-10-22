"""Tests for every element adapter's config-to-model and model-to-device mappings."""

import pytest

from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.schema.elements import ElementType

from .normalize import normalize_for_compare, segment_order
from .test_data import CREATE_CASES, OUTPUTS_CASES, CreateCase, OutputsCase


@pytest.mark.parametrize("element_type", ELEMENT_TYPES)
def test_every_element_type_has_cases(element_type: ElementType) -> None:
    """Each registered adapter has at least one create case and one outputs case."""
    assert any(case["data"]["element_type"] == element_type for case in CREATE_CASES)
    assert any(case["data"]["element_type"] == element_type for case in OUTPUTS_CASES)


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: f"{c['data']['element_type']}: {c['description']}")
def test_model_elements(case: CreateCase) -> None:
    """The adapter turns loaded config into the expected model elements."""
    result = ELEMENT_TYPES[case["data"]["element_type"]].model_elements(case["data"])

    assert normalize_for_compare(result) == normalize_for_compare(case["model"])
    # Segment order sets which end of a connection the power limit applies to
    assert segment_order(result) == segment_order(case["model"])


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: f"{c['data']['element_type']}: {c['description']}")
def test_outputs(case: OutputsCase) -> None:
    """The adapter maps model outputs to device outputs, called the way the coordinator calls it."""
    data = case["data"]
    result = ELEMENT_TYPES[data["element_type"]].outputs(
        name=data["name"],
        model_outputs=case["model_outputs"],
        config=data,
        periods=case["periods"],
    )

    assert result == case["outputs"]
