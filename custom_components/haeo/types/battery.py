"""Battery element configuration for HAEO integration."""

from typing import Any, Literal, NotRequired, TypedDict

from custom_components.haeo.schema.fields import (
    BatterySOCFieldData,
    BatterySOCFieldSchema,
    BatterySOCSensorFieldData,
    BatterySOCSensorFieldSchema,
    EnergyFieldData,
    EnergyFieldSchema,
    NameFieldData,
    NameFieldSchema,
    PercentageFieldData,
    PercentageFieldSchema,
    PowerFieldData,
    PowerFieldSchema,
    PriceFieldData,
    PriceFieldSchema,
)


class BatteryConfigSchema(TypedDict):
    """Battery configuration with sensor entity IDs."""

    element_type: Literal["battery"]
    name: NameFieldSchema
    capacity: EnergyFieldSchema
    initial_charge_percentage: BatterySOCSensorFieldSchema
    min_charge_percentage: NotRequired[BatterySOCFieldSchema]
    max_charge_percentage: NotRequired[BatterySOCFieldSchema]
    efficiency: NotRequired[PercentageFieldSchema]
    max_charge_power: NotRequired[PowerFieldSchema]
    max_discharge_power: NotRequired[PowerFieldSchema]
    charge_cost: NotRequired[PriceFieldSchema]
    discharge_cost: NotRequired[PriceFieldSchema]


class BatteryConfigData(TypedDict):
    """Battery configuration with loaded sensor values."""

    element_type: Literal["battery"]
    name: NameFieldData
    capacity: EnergyFieldData
    initial_charge_percentage: BatterySOCSensorFieldData
    min_charge_percentage: NotRequired[BatterySOCFieldData]
    max_charge_percentage: NotRequired[BatterySOCFieldData]
    efficiency: NotRequired[PercentageFieldData]
    max_charge_power: NotRequired[PowerFieldData]
    max_discharge_power: NotRequired[PowerFieldData]
    charge_cost: NotRequired[PriceFieldData]
    discharge_cost: NotRequired[PriceFieldData]


BATTERY_CONFIG_DEFAULTS: dict[str, Any] = {
    "min_charge_percentage": 10.0,
    "max_charge_percentage": 90.0,
    "efficiency": 99.0,
}
