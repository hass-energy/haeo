"""Test data for battery_section element configuration."""

from collections.abc import Sequence

from custom_components.haeo.elements import battery_section as battery_section_element
from custom_components.haeo.elements.battery_section import BatterySectionConfigData
from custom_components.haeo.model import battery as battery_model
from custom_components.haeo.model.const import (
    OUTPUT_TYPE_ENERGY,
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_SHADOW_PRICE,
)
from custom_components.haeo.model.output_data import OutputData

from .types import (
    ElementConfigData,
    ElementConfigSchema,
    ElementValidCase,
    InvalidModelCase,
    InvalidSchemaCase,
)

# Test cases for battery_section element
VALID: Sequence[ElementValidCase[ElementConfigSchema, ElementConfigData]] = [
    {
        "description": "Battery section with all shadow prices",
        "element_type": "battery_section",
        "schema": battery_section_element.BatterySectionConfigSchema(
            element_type="battery_section",
            name="test_section",
            capacity=["sensor.capacity"],
            initial_charge=["sensor.initial_charge"],
        ),
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
                battery_model.BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-"),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+"),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(5.0, 5.5)),
                battery_model.BATTERY_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                battery_model.BATTERY_ENERGY_IN_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,)),
                battery_model.BATTERY_ENERGY_OUT_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,)),
                battery_model.BATTERY_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,)),
                battery_model.BATTERY_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,)),
            },
        },
        "outputs": {
            battery_section_element.BATTERY_SECTION_DEVICE: {
                battery_section_element.BATTERY_SECTION_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="-"),
                battery_section_element.BATTERY_SECTION_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(0.5,), direction="+"),
                battery_section_element.BATTERY_SECTION_POWER_ACTIVE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(-0.5,), direction=None),
                battery_section_element.BATTERY_SECTION_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(5.0, 5.5)),
                battery_section_element.BATTERY_SECTION_POWER_BALANCE: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kW", values=(0.01,)),
                battery_section_element.BATTERY_SECTION_ENERGY_IN_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.003,)),
                battery_section_element.BATTERY_SECTION_ENERGY_OUT_FLOW: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.004,)),
                battery_section_element.BATTERY_SECTION_SOC_MAX: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.005,)),
                battery_section_element.BATTERY_SECTION_SOC_MIN: OutputData(type=OUTPUT_TYPE_SHADOW_PRICE, unit="$/kWh", values=(0.006,)),
            },
        },
    },
    {
        "description": "Battery section without optional shadow prices",
        "element_type": "battery_section",
        "schema": battery_section_element.BatterySectionConfigSchema(
            element_type="battery_section",
            name="test_section_minimal",
            capacity=["sensor.capacity"],
            initial_charge=["sensor.initial_charge"],
        ),
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
                battery_model.BATTERY_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(2.0,), direction="-"),
                battery_model.BATTERY_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="+"),
                battery_model.BATTERY_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(5.0, 4.0)),
                # No optional shadow prices
            },
        },
        "outputs": {
            battery_section_element.BATTERY_SECTION_DEVICE: {
                battery_section_element.BATTERY_SECTION_POWER_CHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(2.0,), direction="-"),
                battery_section_element.BATTERY_SECTION_POWER_DISCHARGE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(1.0,), direction="+"),
                battery_section_element.BATTERY_SECTION_POWER_ACTIVE: OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=(-1.0,), direction=None),
                battery_section_element.BATTERY_SECTION_ENERGY_STORED: OutputData(type=OUTPUT_TYPE_ENERGY, unit="kWh", values=(5.0, 4.0)),
            },
        },
    },
]

# Invalid schema-only cases
INVALID_SCHEMA: Sequence[InvalidSchemaCase[ElementConfigSchema]] = []

# Invalid model parameter combinations
INVALID_MODEL_PARAMS: Sequence[InvalidModelCase[ElementConfigData]] = []
