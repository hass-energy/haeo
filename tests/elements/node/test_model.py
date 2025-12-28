"""Tests for node element model mapping.

These tests verify that node adapters correctly:
1. Transform ConfigData into model element definitions
2. Map model outputs back to device outputs
"""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import pytest

from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.elements import node as node_element
from custom_components.haeo.elements.node import NodeConfigData
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.const import OUTPUT_TYPE_SHADOW_PRICE
from custom_components.haeo.model.node import NODE_POWER_BALANCE
from custom_components.haeo.model.output_data import OutputData


class ValidCase(TypedDict):
    """Test case structure for valid node configurations."""

    description: str
    data: NodeConfigData
    model: list[dict[str, Any]]
    model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
    outputs: Mapping[str, Mapping[str, OutputData]]


VALID_CASES: Sequence[ValidCase] = [
    {
        "description": "Node as passthrough",
        "data": NodeConfigData(
            element_type="node",
            name="node_main",
            is_source=False,
            is_sink=False,
        ),
        "model": [
            {"element_type": "node", "name": "node_main", "is_source": False, "is_sink": False},
        ],
        "model_outputs": {
            "node_main": {
                NODE_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.0,)),
            }
        },
        "outputs": {
            node_element.NODE_DEVICE_NODE: {
                node_element.NODE_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.0,)),
            }
        },
    },
]


def _case_id(case: ValidCase) -> str:
    return case["description"]


@pytest.mark.parametrize("case", VALID_CASES, ids=_case_id)
def test_create_model_elements(case: ValidCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES["node"]
    result = entry.create_model_elements(case["data"])
    assert result == case["model"]


@pytest.mark.parametrize("case", VALID_CASES, ids=_case_id)
def test_outputs_mapping(case: ValidCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES["node"]
    result = entry.outputs(case["data"]["name"], case["model_outputs"], case["data"])
    assert result == case["outputs"]
