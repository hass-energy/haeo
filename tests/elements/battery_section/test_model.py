"""Tests for battery_section element model mapping.

These tests verify that battery_section adapters correctly:
1. Transform ConfigData into model element definitions
2. Map model outputs back to device outputs
"""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import pytest

from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.elements import battery_section as battery_section_element
from custom_components.haeo.elements.battery_section import BatterySectionConfigData
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model import battery as battery_model
from custom_components.haeo.model.const import OUTPUT_TYPE_ENERGY, OUTPUT_TYPE_POWER, OUTPUT_TYPE_SHADOW_PRICE
from custom_components.haeo.model.output_data import OutputData


class ValidCase(TypedDict):
    """Test case structure for valid battery_section configurations."""

    description: str
    data: BatterySectionConfigData
    model: list[dict[str, Any]]
    model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
    outputs: Mapping[str, Mapping[str, OutputData]]


VALID_CASES: Sequence[ValidCase] = [
    {
        "description": "Battery section with all shadow prices",
        "data": BatterySectionConfigData(
            element_type="battery_section",
            name="test_section",
            capacity=[10.0],
            initial_charge=[5.0],
        ),
        "model": [
            {
                "element_type": "battery",
                "name": "test_section",
                "capacity": [10.0],
                "initial_charge": 5.0,
            },
        ],
        "model_outputs": {
            "test_section": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-"
                ),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+"
                ),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(5.0, 5.5)),
                battery_model.BATTERY_POWER_BALANCE: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)
                ),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,)
                ),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,)
                ),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,)),
            },
        },
        "outputs": {
            battery_section_element.BATTERY_SECTION_DEVICE: {
                battery_section_element.BATTERY_SECTION_POWER_CHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-"
                ),
                battery_section_element.BATTERY_SECTION_POWER_DISCHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+"
                ),
                battery_section_element.BATTERY_SECTION_POWER_ACTIVE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(-0.5,), direction=None
                ),
                battery_section_element.BATTERY_SECTION_ENERGY_STORED: OutputData(
                    type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(5.0, 5.5)
                ),
                battery_section_element.BATTERY_SECTION_POWER_BALANCE: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)
                ),
                battery_section_element.BATTERY_SECTION_ENERGY_IN_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,)
                ),
                battery_section_element.BATTERY_SECTION_ENERGY_OUT_FLOW: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,)
                ),
                battery_section_element.BATTERY_SECTION_SOC_MAX: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,)
                ),
                battery_section_element.BATTERY_SECTION_SOC_MIN: OutputData(
                    type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,)
                ),
            },
        },
    },
    {
        "description": "Battery section without optional shadow prices",
        "data": BatterySectionConfigData(
            element_type="battery_section",
            name="test_section_minimal",
            capacity=[10.0],
            initial_charge=[5.0],
        ),
        "model": [
            {
                "element_type": "battery",
                "name": "test_section_minimal",
                "capacity": [10.0],
                "initial_charge": 5.0,
            },
        ],
        "model_outputs": {
            "test_section_minimal": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(2.0,), direction="-"
                ),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="+"
                ),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(5.0, 4.0)),
            },
        },
        "outputs": {
            battery_section_element.BATTERY_SECTION_DEVICE: {
                battery_section_element.BATTERY_SECTION_POWER_CHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(2.0,), direction="-"
                ),
                battery_section_element.BATTERY_SECTION_POWER_DISCHARGE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="+"
                ),
                battery_section_element.BATTERY_SECTION_POWER_ACTIVE: OutputData(
                    type=OUTPUT_TYPE_POWER, unit="kW", values=(-1.0,), direction=None
                ),
                battery_section_element.BATTERY_SECTION_ENERGY_STORED: OutputData(
                    type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(5.0, 4.0)
                ),
            },
        },
    },
]


def _case_id(case: ValidCase) -> str:
    return case["description"]


@pytest.mark.parametrize("case", VALID_CASES, ids=_case_id)
def test_create_model_elements(case: ValidCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES["battery_section"]
    result = entry.create_model_elements(case["data"])
    assert result == case["model"]


@pytest.mark.parametrize("case", VALID_CASES, ids=_case_id)
def test_outputs_mapping(case: ValidCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES["battery_section"]
    result = entry.outputs(case["data"]["name"], case["model_outputs"], case["data"])
    assert result == case["outputs"]
