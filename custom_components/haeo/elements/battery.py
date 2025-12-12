"""Battery element configuration for HAEO integration."""

from collections.abc import Mapping
from typing import Any, Final, Literal, NotRequired, TypedDict

from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model import battery as model_battery
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.schema.fields import (
    BatterySOCFieldData,
    BatterySOCFieldSchema,
    BatterySOCSensorFieldData,
    BatterySOCSensorFieldSchema,
    ElementNameFieldSchema,
    EnergySensorFieldData,
    EnergySensorFieldSchema,
    NameFieldData,
    NameFieldSchema,
    PercentageFieldData,
    PercentageFieldSchema,
    PowerSensorFieldData,
    PowerSensorFieldSchema,
    PriceFieldData,
    PriceFieldSchema,
    PriceSensorsFieldData,
    PriceSensorsFieldSchema,
)

ELEMENT_TYPE: Final = "battery"

# Device names for battery devices (used for translations)
BATTERY_DEVICE_BATTERY: Final = ELEMENT_TYPE
BATTERY_DEVICE_UNDERCHARGE: Final = "battery_device_undercharge"
BATTERY_DEVICE_NORMAL: Final = "battery_device_normal"
BATTERY_DEVICE_OVERCHARGE: Final = "battery_device_overcharge"

type BatteryDeviceName = Literal[
    "battery",
    "battery_device_undercharge",
    "battery_device_normal",
    "battery_device_overcharge",
]

BATTERY_DEVICE_NAMES: Final[frozenset[BatteryDeviceName]] = frozenset(
    (
        BATTERY_DEVICE_BATTERY,
        BATTERY_DEVICE_UNDERCHARGE,
        BATTERY_DEVICE_NORMAL,
        BATTERY_DEVICE_OVERCHARGE,
    )
)

# Configuration field names
CONF_CAPACITY: Final = "capacity"
CONF_INITIAL_CHARGE_PERCENTAGE: Final = "initial_charge_percentage"
CONF_MIN_CHARGE_PERCENTAGE: Final = "min_charge_percentage"
CONF_MAX_CHARGE_PERCENTAGE: Final = "max_charge_percentage"
CONF_EFFICIENCY: Final = "efficiency"
CONF_MAX_CHARGE_POWER: Final = "max_charge_power"
CONF_MAX_DISCHARGE_POWER: Final = "max_discharge_power"
CONF_EARLY_CHARGE_INCENTIVE: Final = "early_charge_incentive"
CONF_DISCHARGE_COST: Final = "discharge_cost"
CONF_UNDERCHARGE_PERCENTAGE: Final = "undercharge_percentage"
CONF_OVERCHARGE_PERCENTAGE: Final = "overcharge_percentage"
CONF_UNDERCHARGE_COST: Final = "undercharge_cost"
CONF_OVERCHARGE_COST: Final = "overcharge_cost"
CONF_CONNECTION: Final = "connection"

# Battery-specific sensor names (for translation/output mapping)
BATTERY_POWER_CHARGE: Final = "battery_power_charge"
BATTERY_POWER_DISCHARGE: Final = "battery_power_discharge"
BATTERY_ENERGY_STORED: Final = "battery_energy_stored"
BATTERY_STATE_OF_CHARGE: Final = "battery_state_of_charge"
BATTERY_POWER_BALANCE: Final = "battery_power_balance"
BATTERY_CHARGE_PRICE: Final = "battery_charge_price"
BATTERY_DISCHARGE_PRICE: Final = "battery_discharge_price"
BATTERY_ENERGY_IN_FLOW: Final = "battery_energy_in_flow"
BATTERY_ENERGY_OUT_FLOW: Final = "battery_energy_out_flow"
BATTERY_SOC_MAX: Final = "battery_soc_max"
BATTERY_SOC_MIN: Final = "battery_soc_min"


type BatteryOutputName = Literal[
    "battery_power_charge",
    "battery_power_discharge",
    "battery_energy_stored",
    "battery_state_of_charge",
    "battery_power_balance",
    "battery_charge_price",
    "battery_discharge_price",
    "battery_energy_in_flow",
    "battery_energy_out_flow",
    "battery_soc_max",
    "battery_soc_min",
]

BATTERY_OUTPUT_NAMES: Final[frozenset[BatteryOutputName]] = frozenset(
    (
        BATTERY_POWER_CHARGE,
        BATTERY_POWER_DISCHARGE,
        BATTERY_ENERGY_STORED,
        BATTERY_STATE_OF_CHARGE,
        BATTERY_POWER_BALANCE,
        BATTERY_CHARGE_PRICE,
        BATTERY_DISCHARGE_PRICE,
        BATTERY_ENERGY_IN_FLOW,
        BATTERY_ENERGY_OUT_FLOW,
        BATTERY_SOC_MAX,
        BATTERY_SOC_MIN,
    )
)


class BatteryConfigSchema(TypedDict):
    """Battery configuration with sensor entity IDs."""

    element_type: Literal["battery"]
    name: NameFieldSchema
    connection: ElementNameFieldSchema  # Connection ID that battery connects to
    capacity: EnergySensorFieldSchema
    initial_charge_percentage: BatterySOCSensorFieldSchema
    min_charge_percentage: BatterySOCFieldSchema
    max_charge_percentage: BatterySOCFieldSchema
    efficiency: PercentageFieldSchema
    max_charge_power: NotRequired[PowerSensorFieldSchema]
    max_discharge_power: NotRequired[PowerSensorFieldSchema]
    early_charge_incentive: NotRequired[PriceFieldSchema]
    discharge_cost: NotRequired[PriceSensorsFieldSchema]
    undercharge_percentage: NotRequired[BatterySOCFieldSchema]
    overcharge_percentage: NotRequired[BatterySOCFieldSchema]
    undercharge_cost: NotRequired[PriceSensorsFieldSchema]
    overcharge_cost: NotRequired[PriceSensorsFieldSchema]


class BatteryConfigData(TypedDict):
    """Battery configuration with loaded sensor values."""

    element_type: Literal["battery"]
    name: NameFieldData
    connection: ElementNameFieldSchema  # Connection ID that battery connects to
    capacity: EnergySensorFieldData
    initial_charge_percentage: BatterySOCSensorFieldData
    min_charge_percentage: BatterySOCFieldData
    max_charge_percentage: BatterySOCFieldData
    efficiency: PercentageFieldData
    max_charge_power: NotRequired[PowerSensorFieldData]
    max_discharge_power: NotRequired[PowerSensorFieldData]
    early_charge_incentive: NotRequired[PriceFieldData]
    discharge_cost: NotRequired[PriceSensorsFieldData]
    undercharge_percentage: NotRequired[BatterySOCFieldData]
    overcharge_percentage: NotRequired[BatterySOCFieldData]
    undercharge_cost: NotRequired[PriceSensorsFieldData]
    overcharge_cost: NotRequired[PriceSensorsFieldData]


CONFIG_DEFAULTS: dict[str, Any] = {
    CONF_MIN_CHARGE_PERCENTAGE: 10.0,
    CONF_MAX_CHARGE_PERCENTAGE: 90.0,
    CONF_EFFICIENCY: 99.0,
}


def create_model_elements(config: BatteryConfigData) -> list[dict[str, Any]]:
    """Create model elements for Battery configuration."""
    return [
        {
            "element_type": "battery",
            "name": config["name"],
            "capacity": config["capacity"],
            "initial_charge_percentage": config["initial_charge_percentage"],
            "min_charge_percentage": config["min_charge_percentage"],
            "max_charge_percentage": config["max_charge_percentage"],
            "early_charge_incentive": config.get("early_charge_incentive"),
            "undercharge_percentage": config.get("undercharge_percentage"),
            "overcharge_percentage": config.get("overcharge_percentage"),
            "undercharge_cost": config.get("undercharge_cost"),
            "overcharge_cost": config.get("overcharge_cost"),
        },
        {
            "element_type": "connection",
            "name": f"{config['name']}:connection",
            "source": config["name"],
            "target": config["connection"],
            "efficiency_source_target": config["efficiency"],  # Battery to network (discharge)
            "efficiency_target_source": config["efficiency"],  # Network to battery (charge)
            "max_power_source_target": config.get("max_discharge_power"),
            "max_power_target_source": config.get("max_charge_power"),
            "price_source_target": config.get("discharge_cost"),  # Discharge cost (minimum margin)
        },
    ]


def outputs(
    name: str, outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
) -> Mapping[BatteryDeviceName, Mapping[BatteryOutputName, OutputData]]:
    """Map model outputs to battery-specific output names.

    Returns multiple devices for SOC regions based on what's configured.
    Always returns aggregate device. Only returns region devices if their outputs exist.
    """
    battery = outputs[name]

    # Aggregate device outputs (total power and energy across all regions)
    aggregate_outputs: dict[BatteryOutputName, OutputData] = {
        BATTERY_POWER_CHARGE: battery[model_battery.BATTERY_POWER_CHARGE],
        BATTERY_POWER_DISCHARGE: battery[model_battery.BATTERY_POWER_DISCHARGE],
        BATTERY_ENERGY_STORED: battery[model_battery.BATTERY_ENERGY_STORED],
        BATTERY_STATE_OF_CHARGE: battery[model_battery.BATTERY_STATE_OF_CHARGE],
        BATTERY_POWER_BALANCE: battery[model_battery.BATTERY_POWER_BALANCE],
    }

    result: dict[BatteryDeviceName, dict[BatteryOutputName, OutputData]] = {BATTERY_DEVICE_BATTERY: aggregate_outputs}

    # Undercharge region device outputs (only if configured)
    if model_battery.BATTERY_UNDERCHARGE_ENERGY_STORED in battery:
        undercharge_outputs: dict[BatteryOutputName, OutputData] = {
            BATTERY_ENERGY_STORED: battery[model_battery.BATTERY_UNDERCHARGE_ENERGY_STORED],
            BATTERY_POWER_CHARGE: battery[model_battery.BATTERY_UNDERCHARGE_POWER_CHARGE],
            BATTERY_POWER_DISCHARGE: battery[model_battery.BATTERY_UNDERCHARGE_POWER_DISCHARGE],
            BATTERY_CHARGE_PRICE: battery[model_battery.BATTERY_UNDERCHARGE_CHARGE_PRICE],
            BATTERY_DISCHARGE_PRICE: battery[model_battery.BATTERY_UNDERCHARGE_DISCHARGE_PRICE],
            BATTERY_ENERGY_IN_FLOW: battery[model_battery.BATTERY_UNDERCHARGE_ENERGY_IN_FLOW],
            BATTERY_ENERGY_OUT_FLOW: battery[model_battery.BATTERY_UNDERCHARGE_ENERGY_OUT_FLOW],
            BATTERY_SOC_MAX: battery[model_battery.BATTERY_UNDERCHARGE_SOC_MAX],
            BATTERY_SOC_MIN: battery[model_battery.BATTERY_UNDERCHARGE_SOC_MIN],
        }
        result[BATTERY_DEVICE_UNDERCHARGE] = undercharge_outputs

    # Normal region device outputs (only if configured)
    if model_battery.BATTERY_NORMAL_ENERGY_STORED in battery:
        normal_outputs: dict[BatteryOutputName, OutputData] = {
            BATTERY_ENERGY_STORED: battery[model_battery.BATTERY_NORMAL_ENERGY_STORED],
            BATTERY_POWER_CHARGE: battery[model_battery.BATTERY_NORMAL_POWER_CHARGE],
            BATTERY_POWER_DISCHARGE: battery[model_battery.BATTERY_NORMAL_POWER_DISCHARGE],
            BATTERY_CHARGE_PRICE: battery[model_battery.BATTERY_NORMAL_CHARGE_PRICE],
            BATTERY_DISCHARGE_PRICE: battery[model_battery.BATTERY_NORMAL_DISCHARGE_PRICE],
            BATTERY_ENERGY_IN_FLOW: battery[model_battery.BATTERY_NORMAL_ENERGY_IN_FLOW],
            BATTERY_ENERGY_OUT_FLOW: battery[model_battery.BATTERY_NORMAL_ENERGY_OUT_FLOW],
            BATTERY_SOC_MAX: battery[model_battery.BATTERY_NORMAL_SOC_MAX],
            BATTERY_SOC_MIN: battery[model_battery.BATTERY_NORMAL_SOC_MIN],
        }
        result[BATTERY_DEVICE_NORMAL] = normal_outputs

    # Overcharge region device outputs (only if configured)
    if model_battery.BATTERY_OVERCHARGE_ENERGY_STORED in battery:
        overcharge_outputs: dict[BatteryOutputName, OutputData] = {
            BATTERY_ENERGY_STORED: battery[model_battery.BATTERY_OVERCHARGE_ENERGY_STORED],
            BATTERY_POWER_CHARGE: battery[model_battery.BATTERY_OVERCHARGE_POWER_CHARGE],
            BATTERY_POWER_DISCHARGE: battery[model_battery.BATTERY_OVERCHARGE_POWER_DISCHARGE],
            BATTERY_CHARGE_PRICE: battery[model_battery.BATTERY_OVERCHARGE_CHARGE_PRICE],
            BATTERY_DISCHARGE_PRICE: battery[model_battery.BATTERY_OVERCHARGE_DISCHARGE_PRICE],
            BATTERY_ENERGY_IN_FLOW: battery[model_battery.BATTERY_OVERCHARGE_ENERGY_IN_FLOW],
            BATTERY_ENERGY_OUT_FLOW: battery[model_battery.BATTERY_OVERCHARGE_ENERGY_OUT_FLOW],
            BATTERY_SOC_MAX: battery[model_battery.BATTERY_OVERCHARGE_SOC_MAX],
            BATTERY_SOC_MIN: battery[model_battery.BATTERY_OVERCHARGE_SOC_MIN],
        }
        result[BATTERY_DEVICE_OVERCHARGE] = overcharge_outputs

    return result
