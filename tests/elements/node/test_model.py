"""Tests for node element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import pytest

from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.elements import node as node_element
from custom_components.haeo.elements.node import NodeConfigData
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements.node import NODE_POWER_BALANCE
from custom_components.haeo.model.output_data import OutputData


class CreateCase(TypedDict):
    """Test case for model_elements."""

    description: str
    data: NodeConfigData
    model: list[dict[str, Any]]


class OutputsCase(TypedDict):
    """Test case for outputs mapping."""

    description: str
    name: str
    model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
    outputs: Mapping[str, Mapping[str, OutputData]]


CREATE_CASES: Sequence[CreateCase] = [
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
    },
]


OUTPUTS_CASES: Sequence[OutputsCase] = [
    {
        "description": "Node with power balance",
        "name": "node_main",
        "model_outputs": {
            "node_main": {
                NODE_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.0,)),
            }
        },
        "outputs": {
            node_element.NODE_DEVICE_NODE: {
                node_element.NODE_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.0,)),
            }
        },
    },
]


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES["node"]
    result = entry.model_elements(case["data"])
    assert result == case["model"]


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES["node"]
    result = entry.outputs(case["name"], case["model_outputs"])
    assert result == case["outputs"]
