"""Adapter mapping cases for the battery_section element."""

import numpy as np

from custom_components.haeo.core.adapters.elements.battery_section import (
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
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_BATTERY
from custom_components.haeo.core.model.elements import battery as battery_model
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.battery_section import BatterySectionConfigData

from . import CreateCase, OutputsCase

SECTION = BatterySectionConfigData(
    element_type=ElementType.BATTERY_SECTION,
    name="test_section",
    storage={
        "capacity": np.array([10.0]),
        "initial_charge": 5.0,
    },
)

CREATE_CASES: list[CreateCase] = [
    {
        "description": "Battery section basic",
        "data": SECTION,
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


OUTPUTS_CASES: list[OutputsCase] = [
    {
        "description": "Battery section with all shadow prices",
        "data": SECTION,
        "model_outputs": {
            "test_section": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(
                    type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"
                ),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"
                ),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(5.0, 5.5)),
                battery_model.BATTERY_POWER_BALANCE: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.01,)
                ),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.003,)
                ),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.004,)
                ),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.005,)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.006,)),
            },
        },
        "periods": np.array([1.0]),
        "outputs": {
            BATTERY_SECTION_DEVICE: {
                BATTERY_SECTION_POWER_CHARGE: OutputData(
                    type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"
                ),
                BATTERY_SECTION_POWER_DISCHARGE: OutputData(
                    type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"
                ),
                BATTERY_SECTION_POWER_ACTIVE: OutputData(
                    type=OutputType.POWER, unit="kW", values=(-0.5,), direction=None
                ),
                BATTERY_SECTION_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(5.0, 5.5)),
                BATTERY_SECTION_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.01,)),
                BATTERY_SECTION_ENERGY_IN_FLOW: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.003,)),
                BATTERY_SECTION_ENERGY_OUT_FLOW: OutputData(
                    type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.004,)
                ),
                BATTERY_SECTION_SOC_MAX: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.005,)),
                BATTERY_SECTION_SOC_MIN: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.006,)),
            },
        },
    },
    {
        "description": "Battery section without optional shadow prices",
        "data": SECTION,
        "model_outputs": {
            "test_section": {
                battery_model.BATTERY_POWER_CHARGE: OutputData(
                    type=OutputType.POWER, unit="kW", values=(2.0,), direction="-"
                ),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(
                    type=OutputType.POWER, unit="kW", values=(1.0,), direction="+"
                ),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(5.0, 4.0)),
            },
        },
        "periods": np.array([1.0]),
        "outputs": {
            BATTERY_SECTION_DEVICE: {
                BATTERY_SECTION_POWER_CHARGE: OutputData(
                    type=OutputType.POWER, unit="kW", values=(2.0,), direction="-"
                ),
                BATTERY_SECTION_POWER_DISCHARGE: OutputData(
                    type=OutputType.POWER, unit="kW", values=(1.0,), direction="+"
                ),
                BATTERY_SECTION_POWER_ACTIVE: OutputData(
                    type=OutputType.POWER, unit="kW", values=(-1.0,), direction=None
                ),
                BATTERY_SECTION_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(5.0, 4.0)),
            },
        },
    },
]
