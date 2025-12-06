"""Battery element configuration for HAEO integration."""

from collections.abc import Mapping
from typing import Any, Final, Literal, NotRequired, TypedDict

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


def create_model_elements(
    config: BatteryConfigData,
    period: float,
    n_periods: int,
) -> list[dict[str, Any]]:
    """Create model elements for Battery configuration.

    Returns a list of element configurations that should be added to the network:
    - A Battery element with all SOC/pricing configuration
    - A Connection to/from the battery with power limits and efficiency

    Args:
        config: Battery configuration data
        period: Time period in hours
        n_periods: Number of periods

    Returns:
        List of element configs to add to network

    """
    elements: list[dict[str, Any]] = []

    # Create Battery element (handles SOC tracking, ordering costs)
    battery_config: dict[str, Any] = {
        "element_type": "battery",
        "name": config["name"],
        "capacity": config["capacity"],
        "initial_charge_percentage": config["initial_charge_percentage"],
        "min_charge_percentage": config["min_charge_percentage"],
        "max_charge_percentage": config["max_charge_percentage"],
    }

    # Add optional ordering cost parameters (handled by Battery model)
    if "early_charge_incentive" in config:
        battery_config["early_charge_incentive"] = config["early_charge_incentive"]
    if "undercharge_percentage" in config:
        battery_config["undercharge_percentage"] = config["undercharge_percentage"]
    if "overcharge_percentage" in config:
        battery_config["overcharge_percentage"] = config["overcharge_percentage"]
    if "undercharge_cost" in config:
        battery_config["undercharge_cost"] = config["undercharge_cost"]
    if "overcharge_cost" in config:
        battery_config["overcharge_cost"] = config["overcharge_cost"]

    elements.append(battery_config)

    # Create Connection from battery to node (bidirectional for charge/discharge)
    efficiency_ratio = config["efficiency"] / 100.0  # Convert percentage to ratio
    connection_config: dict[str, Any] = {
        "element_type": "connection",
        "name": f"{config['name']}_connection",
        "source": config["name"],
        "target": config["connection"],
        "efficiency_source_target": efficiency_ratio,  # Battery to network (discharge)
        "efficiency_target_source": efficiency_ratio,  # Network to battery (charge)
    }

    # Add discharge limit (source->target: battery TO network)
    if "max_discharge_power" in config:
        connection_config["max_power_source_target"] = config["max_discharge_power"]

    # Add charge limit (target->source: network TO battery)
    if "max_charge_power" in config:
        connection_config["max_power_target_source"] = config["max_charge_power"]

    # Add discharge cost (source->target: battery TO network)
    if "discharge_cost" in config:
        connection_config["price_source_target"] = config["discharge_cost"]

    elements.append(connection_config)

    return elements


def outputs(
    element_name: str,
    model_outputs: Mapping[str, OutputData],
) -> dict[str, dict[str, OutputData]]:
    """Map model outputs to battery-specific output names.

    Battery model already provides element-specific names, so this is primarily
    a pass-through with structure formatting.

    Args:
        element_name: Name of the battery element
        model_outputs: Outputs from the Battery model

    Returns:
        Nested dict mapping {element_name: {sensor_name: OutputData}}

    """
    battery_outputs: dict[str, OutputData] = {}

    # Battery model outputs are already element-specific, pass through directly
    # Include key outputs: power_charge, power_discharge, energy_stored, state_of_charge
    battery_outputs = {
        output_name: output_data
        for output_name, output_data in model_outputs.items()
        if output_name
        in (
            BATTERY_POWER_CHARGE,
            BATTERY_POWER_DISCHARGE,
            BATTERY_ENERGY_STORED,
            BATTERY_STATE_OF_CHARGE,
        )
        or output_name.startswith("battery_")  # Include all battery outputs
    }

    return {element_name: battery_outputs}
