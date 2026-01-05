"""Tests for battery_section element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import pytest

from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.elements import battery_section as battery_section_element
from custom_components.haeo.elements.battery_section import BatterySectionConfigData
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model import battery as battery_model
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.output_data import OutputData


class CreateCase(TypedDict):
    """Test case for create_model_elements."""

    description: str
    data: BatterySectionConfigData
    model: list[dict[str, Any]]


class OutputsCase(TypedDict):
    """Test case for outputs mapping."""

    description: str
    name: str
    model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
    outputs: Mapping[str, Mapping[str, OutputData]]


CREATE_CASES: Sequence[CreateCase] = [
    {
        "description": "Battery section basic",
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
    },
]


OUTPUTS_CASES: Sequence[OutputsCase] = [
    {
        "description": "Battery section with all shadow prices",
        "name": "test_section",
        "model_outputs": {
            "test_section": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(name=battery_model.BATTERY_POWER_CHARGE, type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(name=battery_model.BATTERY_POWER_DISCHARGE, type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"),
                battery_model.BATTERY_ENERGY_STORED: OutputData(name=battery_model.BATTERY_ENERGY_STORED, type=OutputType.ENERGY, unit="kWh", values=(5.0, 5.5)),
                battery_model.BATTERY_POWER_BALANCE: OutputData(name=battery_model.BATTERY_POWER_BALANCE, type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(name=battery_model.BATTERY_ENERGY_IN_FLOW, type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.003,)),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(name=battery_model.BATTERY_ENERGY_OUT_FLOW, type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.004,)),
                battery_model.BATTERY_SOC_MAX: OutputData(name=battery_model.BATTERY_SOC_MAX, type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.005,)),
                battery_model.BATTERY_SOC_MIN: OutputData(name=battery_model.BATTERY_SOC_MIN, type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.006,)),
            },
        },
        "outputs": {
            battery_section_element.BATTERY_SECTION_DEVICE: {
                battery_section_element.BATTERY_SECTION_POWER_CHARGE: OutputData(name=battery_section_element.BATTERY_SECTION_POWER_CHARGE, type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"),
                battery_section_element.BATTERY_SECTION_POWER_DISCHARGE: OutputData(name=battery_section_element.BATTERY_SECTION_POWER_DISCHARGE, type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"),
                battery_section_element.BATTERY_SECTION_POWER_ACTIVE: OutputData(name=battery_section_element.BATTERY_SECTION_POWER_ACTIVE, type=OutputType.POWER, unit="kW", values=(-0.5,), direction=None),
                battery_section_element.BATTERY_SECTION_ENERGY_STORED: OutputData(name=battery_section_element.BATTERY_SECTION_ENERGY_STORED, type=OutputType.ENERGY, unit="kWh", values=(5.0, 5.5)),
                battery_section_element.BATTERY_SECTION_POWER_BALANCE: OutputData(name=battery_section_element.BATTERY_SECTION_POWER_BALANCE, type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                battery_section_element.BATTERY_SECTION_ENERGY_IN_FLOW: OutputData(name=battery_section_element.BATTERY_SECTION_ENERGY_IN_FLOW, type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.003,)),
                battery_section_element.BATTERY_SECTION_ENERGY_OUT_FLOW: OutputData(name=battery_section_element.BATTERY_SECTION_ENERGY_OUT_FLOW, type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.004,)),
                battery_section_element.BATTERY_SECTION_SOC_MAX: OutputData(name=battery_section_element.BATTERY_SECTION_SOC_MAX, type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.005,)),
                battery_section_element.BATTERY_SECTION_SOC_MIN: OutputData(name=battery_section_element.BATTERY_SECTION_SOC_MIN, type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.006,)),
            },
        },
    },
    {
        "description": "Battery section without optional shadow prices",
        "name": "test_section_minimal",
        "model_outputs": {
            "test_section_minimal": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(name=battery_model.BATTERY_POWER_CHARGE, type=OutputType.POWER, unit="kW", values=(2.0,), direction="-"),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(name=battery_model.BATTERY_POWER_DISCHARGE, type=OutputType.POWER, unit="kW", values=(1.0,), direction="+"),
                battery_model.BATTERY_ENERGY_STORED: OutputData(name=battery_model.BATTERY_ENERGY_STORED, type=OutputType.ENERGY, unit="kWh", values=(5.0, 4.0)),
            },
        },
        "outputs": {
            battery_section_element.BATTERY_SECTION_DEVICE: {
                battery_section_element.BATTERY_SECTION_POWER_CHARGE: OutputData(name=battery_section_element.BATTERY_SECTION_POWER_CHARGE, type=OutputType.POWER, unit="kW", values=(2.0,), direction="-"),
                battery_section_element.BATTERY_SECTION_POWER_DISCHARGE: OutputData(name=battery_section_element.BATTERY_SECTION_POWER_DISCHARGE, type=OutputType.POWER, unit="kW", values=(1.0,), direction="+"),
                battery_section_element.BATTERY_SECTION_POWER_ACTIVE: OutputData(name=battery_section_element.BATTERY_SECTION_POWER_ACTIVE, type=OutputType.POWER, unit="kW", values=(-1.0,), direction=None),
                battery_section_element.BATTERY_SECTION_ENERGY_STORED: OutputData(name=battery_section_element.BATTERY_SECTION_ENERGY_STORED, type=OutputType.ENERGY, unit="kWh", values=(5.0, 4.0)),
            },
        },
    },
]


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_create_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES["battery_section"]
    result = entry.create_model_elements(case["data"])
    assert result == case["model"]


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES["battery_section"]
    result = entry.outputs(case["name"], case["model_outputs"], {})
    assert result == case["outputs"]
