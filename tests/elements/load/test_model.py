"""Tests for load element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import numpy as np
import pytest

from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.elements import load as load_element
from custom_components.haeo.elements.load import LoadConfigData
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.model.elements import power_connection
from custom_components.haeo.model.output_data import OutputData

from tests.util.normalize import normalize_for_compare


class CreateCase(TypedDict):
    """Test case for model_elements."""

    description: str
    data: LoadConfigData
    model: list[dict[str, Any]]


class OutputsCase(TypedDict):
    """Test case for outputs mapping."""

    description: str
    name: str
    model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
    outputs: Mapping[str, Mapping[str, OutputData]]


CREATE_CASES: Sequence[CreateCase] = [
    {
        "description": "Load with forecast",
        "data": LoadConfigData(
            element_type="load",
            name="load_main",
            connection="network",
            forecast=np.array([1.0, 2.0]),
        ),
        "model": [
            {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "load_main", "is_source": False, "is_sink": True},
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "load_main:connection",
                "source": "load_main",
                "target": "network",
                "max_power_source_target": 0.0,
                "max_power_target_source": [1.0, 2.0],
                "fixed_power": True,
            },
        ],
    },
]


OUTPUTS_CASES: Sequence[OutputsCase] = [
    {
        "description": "Load with forecast",
        "name": "load_main",
        "model_outputs": {
            "load_main:connection": {
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(1.0,), direction="+"),
                power_connection.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)),
            }
        },
        "outputs": {
            load_element.LOAD_DEVICE_LOAD: {
                load_element.LOAD_POWER: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="+"),
                load_element.LOAD_FORECAST_LIMIT_PRICE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)),
            }
        },
    },
]


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES["load"]
    result = entry.model_elements(case["data"])
    assert normalize_for_compare(result) == normalize_for_compare(case["model"])


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES["load"]
    result = entry.outputs(case["name"], case["model_outputs"])
    assert result == case["outputs"]
