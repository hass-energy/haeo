"""Tests for node element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import numpy as np
from numpy.typing import NDArray
import pytest

from custom_components.haeo.core.adapters.elements.node import (
    NODE_DEVICE_NODE,
    NODE_POWER_BALANCE,
    NODE_POWER_BALANCE_ENERGY_PRICE,
)
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.model import ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import ELEMENT_POWER_BALANCE
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_NODE
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
    periods: NDArray[np.floating[Any]]
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
                ELEMENT_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.10,)),
            }
        },
        "periods": np.array([1.0 / 12.0]),
        "outputs": {
            NODE_DEVICE_NODE: {
                NODE_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.10,)),
                NODE_POWER_BALANCE_ENERGY_PRICE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(1.20,)),
            }
        },
    },
    {
        "description": "Unconstrained node without power balance",
        "name": "node_main",
        "model_outputs": {"node_main": {}},
        "periods": np.array([1.0]),
        "outputs": {NODE_DEVICE_NODE: {}},
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
    result = entry.outputs(case["name"], case["model_outputs"], periods=case["periods"])

    expected = case["outputs"]
    assert result.keys() == expected.keys()
    for device_name, device_outputs in expected.items():
        assert result[device_name].keys() == device_outputs.keys()
        for output_name, expected_output in device_outputs.items():
            actual = result[device_name][output_name]
            assert actual.type == expected_output.type
            assert actual.unit == expected_output.unit
            assert len(actual.values) == len(expected_output.values)
            for a, e in zip(actual.values, expected_output.values, strict=True):
                assert a == pytest.approx(e)
