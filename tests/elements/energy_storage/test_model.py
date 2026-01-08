"""Tests for energy_storage element model mapping."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

import pytest

from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.elements import energy_storage as energy_storage_element
from custom_components.haeo.elements.energy_storage import EnergyStorageConfigData
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model import energy_storage as energy_storage_model
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.output_data import OutputData


class CreateCase(TypedDict):
    """Test case for create_model_elements."""

    description: str
    data: EnergyStorageConfigData
    model: list[dict[str, Any]]


class OutputsCase(TypedDict):
    """Test case for outputs mapping."""

    description: str
    name: str
    model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
    outputs: Mapping[str, Mapping[str, OutputData]]


CREATE_CASES: Sequence[CreateCase] = [
    {
        "description": "Energy storage basic",
        "data": EnergyStorageConfigData(
            element_type="energy_storage",
            name="test_storage",
            capacity=[10.0],
            initial_charge=[5.0],
        ),
        "model": [
            {
                "element_type": "energy_storage",
                "name": "test_storage",
                "capacity": [10.0],
                "initial_charge": 5.0,
            },
        ],
    },
]


OUTPUTS_CASES: Sequence[OutputsCase] = [
    {
        "description": "Energy storage with all shadow prices",
        "name": "test_storage",
        "model_outputs": {
            "test_storage": {
                energy_storage_model.ENERGY_STORAGE_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"),
                energy_storage_model.ENERGY_STORAGE_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"),
                energy_storage_model.ENERGY_STORAGE_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(5.0, 5.5)),
                energy_storage_model.ENERGY_STORAGE_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                energy_storage_model.ENERGY_STORAGE_ENERGY_IN_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.003,)),
                energy_storage_model.ENERGY_STORAGE_ENERGY_OUT_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.004,)),
                energy_storage_model.ENERGY_STORAGE_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.005,)),
                energy_storage_model.ENERGY_STORAGE_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.006,)),
            },
        },
        "outputs": {
            energy_storage_element.ENERGY_STORAGE_DEVICE: {
                energy_storage_element.ENERGY_STORAGE_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"),
                energy_storage_element.ENERGY_STORAGE_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"),
                energy_storage_element.ENERGY_STORAGE_POWER_ACTIVE: OutputData(type=OutputType.POWER, unit="kW", values=(-0.5,), direction=None),
                energy_storage_element.ENERGY_STORAGE_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(5.0, 5.5)),
                energy_storage_element.ENERGY_STORAGE_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                energy_storage_element.ENERGY_STORAGE_ENERGY_IN_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.003,)),
                energy_storage_element.ENERGY_STORAGE_ENERGY_OUT_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.004,)),
                energy_storage_element.ENERGY_STORAGE_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.005,)),
                energy_storage_element.ENERGY_STORAGE_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.006,)),
            },
        },
    },
    {
        "description": "Energy storage without optional shadow prices",
        "name": "test_storage_minimal",
        "model_outputs": {
            "test_storage_minimal": {
                energy_storage_model.ENERGY_STORAGE_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(2.0,), direction="-"),
                energy_storage_model.ENERGY_STORAGE_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="+"),
                energy_storage_model.ENERGY_STORAGE_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(5.0, 4.0)),
            },
        },
        "outputs": {
            energy_storage_element.ENERGY_STORAGE_DEVICE: {
                energy_storage_element.ENERGY_STORAGE_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(2.0,), direction="-"),
                energy_storage_element.ENERGY_STORAGE_POWER_DISCHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="+"),
                energy_storage_element.ENERGY_STORAGE_POWER_ACTIVE: OutputData(type=OutputType.POWER, unit="kW", values=(-1.0,), direction=None),
                energy_storage_element.ENERGY_STORAGE_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(5.0, 4.0)),
            },
        },
    },
]


@pytest.mark.parametrize("case", CREATE_CASES, ids=lambda c: c["description"])
def test_model_elements(case: CreateCase) -> None:
    """Verify adapter transforms ConfigData into expected model elements."""
    entry = ELEMENT_TYPES["energy_storage"]
    result = entry.model_elements(case["data"])
    assert result == case["model"]


@pytest.mark.parametrize("case", OUTPUTS_CASES, ids=lambda c: c["description"])
def test_outputs_mapping(case: OutputsCase) -> None:
    """Verify adapter maps model outputs to device outputs."""
    entry = ELEMENT_TYPES["energy_storage"]
    result = entry.outputs(case["name"], case["model_outputs"], {})
    assert result == case["outputs"]
