"""Tests for node element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import pytest
from custom_components.haeo.core.adapters.elements.node import NODE_DEVICE_NODE
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.model import ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.elements.node import NODE_POWER_BALANCE
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.node import NodeConfigData


class CreateCase(TypedDict):
    """Test case for model_elements."""

    description: str
    data: NodeConfigData
    model: list[dict[str, Any]]


class OutputsCase(TypedDict):
    """Test case for outputs mapping."""

    description: str
    name: str
    model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]]
    outputs: Mapping[str, Mapping[str, OutputData]]


CREATE_CASES: Sequence[CreateCase] = [
    {
        "description": "Node as passthrough",
        "data": NodeConfigData(
            element_type=ElementType.NODE,
            name="node_main",
            role={"is_source": False, "is_sink": False},
        ),
        "model": [
            {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "node_main", "is_source": False, "is_sink": False},
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
            NODE_DEVICE_NODE: {
                NODE_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.0,)),
            }
        },
    },
]


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES[ElementType.NODE]
    result = entry.model_elements(case["data"])
    assert result == case["model"]


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES[ElementType.NODE]
    result = entry.outputs(case["name"], case["model_outputs"])
    assert result == case["outputs"]
