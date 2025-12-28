"""Tests for load element model mapping.

These tests verify that load adapters correctly:
1. Transform ConfigData into model element definitions
2. Map model outputs back to device outputs
"""

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
    OUTPUT_TYPE_SHADOW_PRICE,
)
from custom_components.haeo.model.output_data import OutputData


class ValidCase(TypedDict):
    """Test case structure for valid load configurations."""

    description: str
    data: LoadConfigData
    model: list[dict[str, Any]]
    model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
    outputs: Mapping[str, Mapping[str, OutputData]]


VALID_CASES: Sequence[ValidCase] = [
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
        "model_outputs": {
            "load_main:connection": {
                power_connection.CONNECTION_POWER_TARGET_SOURCE: OutputData(
                    type=OUTPUT_TYPE_POWER_FLOW, unit="kW", values=(1.0,), direction="+"
                ),
                power_connection.CONNECTION_POWER_MAX_TARGET_SOURCE: OutputData(
                    type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(2.0,)
                ),
                power_connection.CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)
                ),
            }
        },
        "outputs": {
            load_element.LOAD_DEVICE_LOAD: {
                load_element.LOAD_POWER: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="+"),
                load_element.LOAD_POWER_POSSIBLE: OutputData(type=OUTPUT_TYPE_POWER_LIMIT, unit="kW", values=(2.0,)),
                load_element.LOAD_FORECAST_LIMIT_PRICE: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)
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
    entry = ELEMENT_TYPES["load"]
    result = entry.create_model_elements(case["data"])
    assert result == case["model"]


@pytest.mark.parametrize("case", VALID_CASES, ids=_case_id)
def test_outputs_mapping(case: ValidCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES["load"]
    result = entry.outputs(case["data"]["name"], case["model_outputs"], case["data"])
    assert result == case["outputs"]
