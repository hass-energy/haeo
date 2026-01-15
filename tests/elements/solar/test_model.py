"""Tests for solar element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import pytest

from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.elements import solar as solar_element
from custom_components.haeo.elements.solar import SolarConfigData
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.model.elements import power_connection
from custom_components.haeo.model.output_data import OutputData


class CreateCase(TypedDict):
    """Test case for model_elements."""

    description: str
    data: SolarConfigData
    model: list[dict[str, Any]]


class OutputsCase(TypedDict):
    """Test case for outputs mapping."""

    description: str
    name: str
    model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
    outputs: Mapping[str, Mapping[str, OutputData]]


CREATE_CASES: Sequence[CreateCase] = [
    {
        "description": "Solar with production price",
        "data": SolarConfigData(
            element_type="solar",
            name="pv_main",
            connection="network",
            forecast=[2.0, 1.5],
            price_production=0.15,
            curtailment=False,
        ),
        "model": [
            {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "pv_main", "is_source": True, "is_sink": False},
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "pv_main:connection",
                "source": "pv_main",
                "target": "network",
                "max_power_source_target": [2.0, 1.5],
                "max_power_target_source": 0.0,
                "fixed_power": True,
                "price_source_target": 0.15,
            },
        ],
    },
]


OUTPUTS_CASES: Sequence[OutputsCase] = [
    {
        "description": "Solar with forecast limit",
        "name": "pv_main",
        "model_outputs": {
            "pv_main:connection": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(2.0,), direction="+"),
                power_connection.CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.02,)),
            }
        },
        "outputs": {
            solar_element.SOLAR_DEVICE_SOLAR: {
                solar_element.SOLAR_POWER: OutputData(type=OutputType.POWER, unit="kW", values=(2.0,), direction="+"),
                solar_element.SOLAR_FORECAST_LIMIT: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.02,)),
            }
        },
    },
    {
        "description": "Solar with shadow price output",
        "name": "pv_with_price",
        "model_outputs": {
            "pv_with_price:connection": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(1.5,), direction="+"),
                power_connection.CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.0,)),
            }
        },
        "outputs": {
            solar_element.SOLAR_DEVICE_SOLAR: {
                solar_element.SOLAR_POWER: OutputData(type=OutputType.POWER, unit="kW", values=(1.5,), direction="+"),
                solar_element.SOLAR_FORECAST_LIMIT: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.0,)),
            }
        },
    },
]


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES["solar"]
    result = entry.model_elements(case["data"])
    assert result == case["model"]


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES["solar"]
    result = entry.outputs(case["name"], case["model_outputs"])
    assert result == case["outputs"]
