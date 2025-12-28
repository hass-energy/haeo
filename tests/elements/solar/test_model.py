"""Tests for solar element model mapping.

These tests verify that solar adapters correctly:
1. Transform ConfigData into model element definitions
2. Map model outputs back to device outputs
"""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import pytest

from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.elements import solar as solar_element
from custom_components.haeo.elements.solar import SolarConfigData
from custom_components.haeo.model import ModelOutputName, power_connection
from custom_components.haeo.model.const import (
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_POWER_FLOW,
    OUTPUT_TYPE_POWER_LIMIT,
    OUTPUT_TYPE_SHADOW_PRICE,
)
from custom_components.haeo.model.output_data import OutputData


class ValidCase(TypedDict):
    """Test case structure for valid solar configurations."""

    description: str
    data: SolarConfigData
    model: list[dict[str, Any]]
    model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
    outputs: Mapping[str, Mapping[str, OutputData]]


VALID_CASES: Sequence[ValidCase] = [
    {
        "description": "Solar with production price and no curtailment",
        "data": SolarConfigData(
            element_type="solar",
            name="pv_main",
            connection="network",
            forecast=[2.0, 1.5],
            price_production=0.15,
            curtailment=False,
        ),
        "model": [
            {"element_type": "node", "name": "pv_main", "is_source": True, "is_sink": False},
            {
                "element_type": "connection",
                "name": "pv_main:connection",
                "source": "pv_main",
                "target": "network",
                "max_power_source_target": [2.0, 1.5],
                "max_power_target_source": 0.0,
                "fixed_power": True,
                "price_source_target": 0.15,
            },
        ],
        "model_outputs": {
            "pv_main:connection": {
                power_connection.CONNECTION_POWER_SOURCE_TARGET: OutputData(
                    type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(2.0,), direction="+"
                ),
                power_connection.CONNECTION_POWER_MAX_SOURCE_TARGET: OutputData(
                    type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(2.0,)
                ),
                power_connection.CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)
                ),
            }
        },
        "outputs": {
            solar_element.SOLAR_DEVICE_SOLAR: {
                solar_element.SOLAR_POWER: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(2.0,), direction="+"),
                solar_element.SOLAR_POWER_AVAILABLE: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(2.0,)),
                solar_element.SOLAR_FORECAST_LIMIT: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.02,)
                ),
            }
        },
    },
]


def _case_id(case: ValidCase) -> str:
    return case["description"]


@pytest.mark.parametrize("case", VALID_CASES, ids=_case_id)
def test_create_model_elements(case: ValidCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES["solar"]
    result = entry.create_model_elements(case["data"])
    assert result == case["model"]


@pytest.mark.parametrize("case", VALID_CASES, ids=_case_id)
def test_outputs_mapping(case: ValidCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES["solar"]
    result = entry.outputs(case["data"]["name"], case["model_outputs"], case["data"])
    assert result == case["outputs"]
