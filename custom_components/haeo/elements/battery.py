"""Battery element configuration for HAEO integration."""

from typing import Any, Final, Literal, NotRequired, TypedDict

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

ELEMENT_TYPE: Final = "battery"

CONF_CAPACITY: Final = "capacity"
CONF_INITIAL_CHARGE_PERCENTAGE: Final = "initial_charge_percentage"
CONF_MIN_CHARGE_PERCENTAGE: Final = "min_charge_percentage"
CONF_MAX_CHARGE_PERCENTAGE: Final = "max_charge_percentage"
CONF_EFFICIENCY: Final = "efficiency"
CONF_MAX_CHARGE_POWER: Final = "max_charge_power"
CONF_MAX_DISCHARGE_POWER: Final = "max_discharge_power"
CONF_CHARGE_COST: Final = "charge_cost"
CONF_DISCHARGE_COST: Final = "discharge_cost"


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


CONFIG_DEFAULTS: dict[str, Any] = {
    CONF_MIN_CHARGE_PERCENTAGE: 10.0,
    CONF_MAX_CHARGE_PERCENTAGE: 90.0,
    CONF_EFFICIENCY: 99.0,
}


def model_description(config: BatteryConfigSchema) -> str:
    """Generate device model string from battery configuration."""
    capacity_kwh = config[CONF_CAPACITY]

    charge_kw = config.get(CONF_MAX_CHARGE_POWER)
    discharge_kw = config.get(CONF_MAX_DISCHARGE_POWER)

    if charge_kw is not None and discharge_kw is not None:
        return f"Battery {capacity_kwh:.1f}kWh, {charge_kw:.1f}kW charge / {discharge_kw:.1f}kW discharge"
    return f"Battery {capacity_kwh:.1f}kWh"
