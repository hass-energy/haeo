"""Tests for load element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import pytest

from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.elements import load as load_element
from custom_components.haeo.elements.load import LoadConfigData
from custom_components.haeo.model import ModelOutputName, power_connection
from custom_components.haeo.model.const import (
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_POWER_FLOW,
    OUTPUT_TYPE_POWER_LIMIT,
    OUTPUT_TYPE_PRICE,
    OUTPUT_TYPE_SHADOW_PRICE,
)
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
    {
        "description": "Sheddable load with value",
        "data": LoadConfigData(
            element_type="load",
            name="hvac_load",
            connection="network",
            forecast=[3.0, 3.5],
            sheddable=True,
            value_running=0.35,
        ),
        "model": [
            {"element_type": "node", "name": "hvac_load", "is_source": False, "is_sink": True},
            {
                "element_type": "connection",
                "name": "hvac_load:connection",
                "source": "hvac_load",
                "target": "network",
                "max_power_source_target": 0.0,
                "max_power_target_source": [3.0, 3.5],
                "fixed_power": False,
                "price_target_source": 0.35,
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
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(1.0,), direction="+"),
                power_connection.CONNECTION_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(2.0,)),
                power_connection.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
            }
        },
        "outputs": {
            load_element.LOAD_DEVICE_LOAD: {
                load_element.LOAD_POWER: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="+"),
                load_element.LOAD_POWER_POSSIBLE: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(2.0,)),
                load_element.LOAD_FORECAST_LIMIT_PRICE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
            }
        },
    },
    {
        "description": "Sheddable load with value",
        "name": "hvac_load",
        "model_outputs": {
            "hvac_load:connection": {
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(2.0,), direction="+"),
                power_connection.CONNECTION_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(3.0,)),
                power_connection.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)),
                power_connection.CONNECTION_PRICE_TARGET_SOURCE: OutputData(type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.35,), direction="-"),
            }
        },
        "outputs": {
            load_element.LOAD_DEVICE_LOAD: {
                load_element.LOAD_POWER: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(2.0,), direction="+"),
                load_element.LOAD_POWER_POSSIBLE: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(3.0,)),
                load_element.LOAD_FORECAST_LIMIT_PRICE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)),
                load_element.LOAD_VALUE: OutputData(type=OUTPUT_TYPE_PRICE, unit="$/kWh", values=(0.35,), direction="-"),
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
