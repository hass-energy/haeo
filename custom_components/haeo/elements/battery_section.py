"""Battery section element configuration for HAEO integration.

This is an advanced element that provides direct access to the model layer Battery element.
Unlike the standard Battery element which creates multiple sections and an internal node,
this element creates a single battery section that must be connected manually via Connection.
"""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal, NotRequired, TypedDict

from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model import battery as model_battery
from custom_components.haeo.model.const import OUTPUT_TYPE_POWER, OUTPUT_TYPE_SOC
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.schema.fields import (
    BatterySOCFieldData,
    BatterySOCFieldSchema,
    BatterySOCSensorFieldData,
    BatterySOCSensorFieldSchema,
    EnergySensorFieldData,
    EnergySensorFieldSchema,
    NameFieldData,
    NameFieldSchema,
)

ELEMENT_TYPE: Final = "battery_section"

# Configuration field names
CONF_CAPACITY: Final = "capacity"
CONF_INITIAL_CHARGE_PERCENTAGE: Final = "initial_charge_percentage"
CONF_MIN_CHARGE_PERCENTAGE: Final = "min_charge_percentage"
CONF_MAX_CHARGE_PERCENTAGE: Final = "max_charge_percentage"

type BatterySectionOutputName = Literal[
    "battery_section_power_charge",
    "battery_section_power_discharge",
    "battery_section_power_active",
    "battery_section_energy_stored",
    "battery_section_state_of_charge",
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
        BATTERY_SECTION_STATE_OF_CHARGE := "battery_section_state_of_charge",
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

    A single battery section with explicit SOC bounds. Unlike the standard Battery
    element, this does not create an internal node or implicit connections.
    Connect to other elements using explicit Connection elements.
    """

    element_type: Literal["battery_section"]
    name: NameFieldSchema
    capacity: EnergySensorFieldSchema
    initial_charge_percentage: BatterySOCSensorFieldSchema

    # Optional SOC bounds
    min_charge_percentage: NotRequired[BatterySOCFieldSchema]
    max_charge_percentage: NotRequired[BatterySOCFieldSchema]


class BatterySectionConfigData(TypedDict):
    """Battery section element configuration with loaded values."""

    element_type: Literal["battery_section"]
    name: NameFieldData
    capacity: EnergySensorFieldData
    initial_charge_percentage: BatterySOCSensorFieldData

    # Optional SOC bounds
    min_charge_percentage: NotRequired[BatterySOCFieldData]
    max_charge_percentage: NotRequired[BatterySOCFieldData]


CONFIG_DEFAULTS: dict[str, Any] = {
    CONF_MIN_CHARGE_PERCENTAGE: 0.0,
    CONF_MAX_CHARGE_PERCENTAGE: 100.0,
}


def create_model_elements(config: BatterySectionConfigData) -> list[dict[str, Any]]:
    """Create model elements for BatterySection configuration.

    Creates a single model battery element with the configured capacity and SOC bounds.
    The capacity is scaled by the SOC percentages to create effective min/max bounds.
    """
    name = config["name"]
    capacity = config["capacity"]

    # Get SOC bounds (defaults: 0-100%)
    min_soc = config.get("min_charge_percentage", 0.0) / 100.0
    max_soc = config.get("max_charge_percentage", 100.0) / 100.0

    # Scale capacity by SOC bounds to get effective capacity
    # If min_soc=20% and max_soc=80%, effective capacity is 60% of total
    effective_capacity = [c * (max_soc - min_soc) for c in capacity]

    # Initial charge is relative to total capacity, convert to effective capacity
    initial_soc = config["initial_charge_percentage"][0] / 100.0
    # Clamp initial_soc to within bounds
    clamped_initial_soc = max(min_soc, min(max_soc, initial_soc))
    # Convert to effective capacity (how much above min_soc)
    initial_charge = capacity[0] * (clamped_initial_soc - min_soc)

    return [
        {
            "element_type": "battery",
            "name": name,
            "capacity": effective_capacity,
            "initial_charge": initial_charge,
        }
    ]


def outputs(
    name: str,
    model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]],
    config: BatterySectionConfigData,
) -> Mapping[BatterySectionDeviceName, Mapping[BatterySectionOutputName, OutputData]]:
    """Map model outputs to battery section output names."""
    battery_data = model_outputs[name]
    capacity = config["capacity"]

    # Get min SOC for energy offset calculation
    min_soc = config.get("min_charge_percentage", 0.0) / 100.0

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

    # Energy stored (offset by min_soc * capacity to get absolute energy)
    energy_stored = battery_data[model_battery.BATTERY_ENERGY_STORED]
    absolute_energy = [e + min_soc * c for e, c in zip(energy_stored.values, capacity, strict=False)]
    section_outputs[BATTERY_SECTION_ENERGY_STORED] = replace(energy_stored, values=absolute_energy)

    # State of charge as percentage of total capacity
    soc_values = [e / c * 100.0 if c > 0 else 0.0 for e, c in zip(absolute_energy, capacity, strict=False)]
    section_outputs[BATTERY_SECTION_STATE_OF_CHARGE] = replace(
        energy_stored,
        values=soc_values,
        unit="%",
        type=OUTPUT_TYPE_SOC,
    )

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
