"""Tests for load element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import pytest

from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.elements import load as load_element
from custom_components.haeo.elements.load import LoadConfigData
from custom_components.haeo.model import ModelOutputName, power_connection
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.output_data import OutputData


class CreateCase(TypedDict):
    """Test case for create_model_elements."""

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
            forecast=[1.0, 2.0],
        ),
        "model": [
            {"element_type": "node", "name": "load_main", "is_source": False, "is_sink": True},
            {
                "element_type": "connection",
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
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(name=power_connection.CONNECTION_POWER_TARGET_SOURCE, type=OutputType.POWER_FLOW, unit="kW", values=(1.0,), direction="+"),
                power_connection.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: OutputData(name=power_connection.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE, type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)),
            }
        },
        "outputs": {
            load_element.LOAD_DEVICE_LOAD: {
                load_element.LOAD_POWER: OutputData(name=load_element.LOAD_POWER, type=OutputType.POWER, unit="kW", values=(1.0,), direction="+"),
                load_element.LOAD_FORECAST_LIMIT_PRICE: OutputData(name=load_element.LOAD_FORECAST_LIMIT_PRICE, type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)),
            }
        },
    },
]


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_create_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES["load"]
    result = entry.create_model_elements(case["data"])
    assert result == case["model"]


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES["load"]
    result = entry.outputs(case["name"], case["model_outputs"], {})
    assert result == case["outputs"]
