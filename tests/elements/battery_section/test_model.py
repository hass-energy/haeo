"""Tests for battery_section element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import numpy as np
import pytest

from custom_components.haeo.adapters.elements.battery_section import (
    BATTERY_SECTION_DEVICE,
    BATTERY_SECTION_ENERGY_IN_FLOW,
    BATTERY_SECTION_ENERGY_OUT_FLOW,
    BATTERY_SECTION_ENERGY_STORED,
    BATTERY_SECTION_POWER_ACTIVE,
    BATTERY_SECTION_POWER_BALANCE,
    BATTERY_SECTION_POWER_CHARGE,
    BATTERY_SECTION_POWER_DISCHARGE,
    BATTERY_SECTION_SOC_MAX,
    BATTERY_SECTION_SOC_MIN,
)
from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.schema.elements.battery_section import BatterySectionConfigData
from custom_components.haeo.model import ModelOutputName, ModelOutputValue
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import battery as battery_model
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_BATTERY
from custom_components.haeo.model.output_data import OutputData
from tests.util.normalize import normalize_for_compare


class CreateCase(TypedDict):
    """Test case for model_elements."""

    description: str
    data: BatterySectionConfigData
    model: list[dict[str, Any]]


class OutputsCase(TypedDict):
    """Test case for outputs mapping."""

    description: str
    name: str
    model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]]
    outputs: Mapping[str, Mapping[str, OutputData]]


CREATE_CASES: Sequence[CreateCase] = [
    {
        "description": "Battery section basic",
        "data": BatterySectionConfigData(
            element_type="battery_section",
            common={"name": "test_section"},
            storage={
                "capacity": np.array([10.0]),
                "initial_charge": np.array([5.0]),
            },
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
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
                battery_model.BATTERY_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(5.0, 5.5)),
                battery_model.BATTERY_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.003,)),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.004,)),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.005,)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.006,)),
            },
        },
        "outputs": {
            BATTERY_SECTION_DEVICE: {
                BATTERY_SECTION_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"),
                BATTERY_SECTION_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"),
                BATTERY_SECTION_POWER_ACTIVE: OutputData(type=OutputType.POWER, unit="kW", values=(-0.5,), direction=None),
                BATTERY_SECTION_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(5.0, 5.5)),
                BATTERY_SECTION_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                BATTERY_SECTION_ENERGY_IN_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.003,)),
                BATTERY_SECTION_ENERGY_OUT_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.004,)),
                BATTERY_SECTION_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.005,)),
                BATTERY_SECTION_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.006,)),
            },
        },
    },
    {
        "description": "Battery section without optional shadow prices",
        "name": "test_section_minimal",
        "model_outputs": {
            "test_section_minimal": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(2.0,), direction="-"),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="+"),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(5.0, 4.0)),
            },
        },
        "outputs": {
            BATTERY_SECTION_DEVICE: {
                BATTERY_SECTION_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(2.0,), direction="-"),
                BATTERY_SECTION_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="+"),
                BATTERY_SECTION_POWER_ACTIVE: OutputData(type=OutputType.POWER, unit="kW", values=(-1.0,), direction=None),
                BATTERY_SECTION_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(5.0, 4.0)),
            },
        },
    },
]


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES["battery_section"]
    result = entry.model_elements(case["data"])
    assert normalize_for_compare(result) == normalize_for_compare(case["model"])


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES["battery_section"]
    result = entry.outputs(case["name"], case["model_outputs"])
    assert result == case["outputs"]
