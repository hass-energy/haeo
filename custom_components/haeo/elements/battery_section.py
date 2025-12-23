"""Battery section element configuration for HAEO integration.

This is an advanced element that provides direct access to the model layer Battery element.
Unlike the standard Battery element which creates multiple sections and an internal node,
this element creates a single battery section that must be connected manually via Connection.
"""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal, TypedDict

from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model import battery as model_battery
from custom_components.haeo.model.const import OUTPUT_TYPE_POWER
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.schema.fields import (
    EnergySensorFieldData,
    EnergySensorFieldSchema,
    NameFieldData,
    NameFieldSchema,
)

ELEMENT_TYPE: Final = "battery_section"

# Configuration field names
CONF_CAPACITY: Final = "capacity"
CONF_INITIAL_CHARGE: Final = "initial_charge"

type BatterySectionOutputName = Literal[
    "battery_section_power_charge",
    "battery_section_power_discharge",
    "battery_section_power_active",
    "battery_section_energy_stored",
    "battery_section_power_balance",
    "battery_section_energy_in_flow",
    "battery_section_energy_out_flow",
    "battery_section_soc_max",
    "battery_section_soc_min",
]

BATTERY_SECTION_OUTPUT_NAMES: Final[frozenset[BatterySectionOutputName]] = frozenset(
    (
        BATTERY_SECTION_POWER_CHARGE := "battery_section_power_charge",
        BATTERY_SECTION_POWER_DISCHARGE := "battery_section_power_discharge",
        BATTERY_SECTION_POWER_ACTIVE := "battery_section_power_active",
        BATTERY_SECTION_ENERGY_STORED := "battery_section_energy_stored",
        BATTERY_SECTION_POWER_BALANCE := "battery_section_power_balance",
        BATTERY_SECTION_ENERGY_IN_FLOW := "battery_section_energy_in_flow",
        BATTERY_SECTION_ENERGY_OUT_FLOW := "battery_section_energy_out_flow",
        BATTERY_SECTION_SOC_MAX := "battery_section_soc_max",
        BATTERY_SECTION_SOC_MIN := "battery_section_soc_min",
    )
)

type BatterySectionDeviceName = Literal["battery_section"]

BATTERY_SECTION_DEVICE_NAMES: Final[frozenset[BatterySectionDeviceName]] = frozenset(
    (BATTERY_SECTION_DEVICE := ELEMENT_TYPE,),
)


class BatterySectionConfigSchema(TypedDict):
    """Battery section element configuration.

    A single battery section with capacity and initial charge. Unlike the standard Battery
    element, this does not create an internal node or implicit connections.
    Connect to other elements using explicit Connection elements.
    """

    element_type: Literal["battery_section"]
    name: NameFieldSchema
    capacity: EnergySensorFieldSchema
    initial_charge: EnergySensorFieldSchema


class BatterySectionConfigData(TypedDict):
    """Battery section element configuration with loaded values."""

    element_type: Literal["battery_section"]
    name: NameFieldData
    capacity: EnergySensorFieldData
    initial_charge: EnergySensorFieldData


CONFIG_DEFAULTS: dict[str, Any] = {}


def create_model_elements(config: BatterySectionConfigData) -> list[dict[str, Any]]:
    """Create model elements for BatterySection configuration.

    Direct pass-through to the model battery element.
    """
    return [
        {
            "element_type": "battery",
            "name": config["name"],
            "capacity": config["capacity"],
            "initial_charge": config["initial_charge"][0],
        }
    ]


def outputs(
    name: str,
    model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]],
    _config: BatterySectionConfigData,
) -> Mapping[BatterySectionDeviceName, Mapping[BatterySectionOutputName, OutputData]]:
    """Map model outputs to battery section output names."""
    battery_data = model_outputs[name]

    section_outputs: dict[BatterySectionOutputName, OutputData] = {}

    # Power outputs
    section_outputs[BATTERY_SECTION_POWER_CHARGE] = replace(
        battery_data[model_battery.BATTERY_POWER_CHARGE], type=OUTPUT_TYPE_POWER
    )
    section_outputs[BATTERY_SECTION_POWER_DISCHARGE] = replace(
        battery_data[model_battery.BATTERY_POWER_DISCHARGE], type=OUTPUT_TYPE_POWER
    )

    # Active power (discharge - charge)
    charge_values = battery_data[model_battery.BATTERY_POWER_CHARGE].values
    discharge_values = battery_data[model_battery.BATTERY_POWER_DISCHARGE].values
    section_outputs[BATTERY_SECTION_POWER_ACTIVE] = replace(
        battery_data[model_battery.BATTERY_POWER_CHARGE],
        values=[d - c for c, d in zip(charge_values, discharge_values, strict=True)],
        direction=None,
        type=OUTPUT_TYPE_POWER,
    )

    # Energy stored
    section_outputs[BATTERY_SECTION_ENERGY_STORED] = battery_data[model_battery.BATTERY_ENERGY_STORED]

    # Shadow prices
    if model_battery.BATTERY_POWER_BALANCE in battery_data:
        section_outputs[BATTERY_SECTION_POWER_BALANCE] = battery_data[model_battery.BATTERY_POWER_BALANCE]
    if model_battery.BATTERY_ENERGY_IN_FLOW in battery_data:
        section_outputs[BATTERY_SECTION_ENERGY_IN_FLOW] = battery_data[model_battery.BATTERY_ENERGY_IN_FLOW]
    if model_battery.BATTERY_ENERGY_OUT_FLOW in battery_data:
        section_outputs[BATTERY_SECTION_ENERGY_OUT_FLOW] = battery_data[model_battery.BATTERY_ENERGY_OUT_FLOW]
    if model_battery.BATTERY_SOC_MAX in battery_data:
        section_outputs[BATTERY_SECTION_SOC_MAX] = battery_data[model_battery.BATTERY_SOC_MAX]
    if model_battery.BATTERY_SOC_MIN in battery_data:
        section_outputs[BATTERY_SECTION_SOC_MIN] = battery_data[model_battery.BATTERY_SOC_MIN]

    return {BATTERY_SECTION_DEVICE: section_outputs}
