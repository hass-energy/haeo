"""Battery element configuration for HAEO integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Annotated, Any, Final, Literal, NotRequired, TypedDict

import numpy as np

from custom_components.haeo.model import OUTPUT_TYPE_PRICE, ModelOutputName
from custom_components.haeo.model import battery as model_battery
from custom_components.haeo.model.const import OUTPUT_TYPE_POWER, OUTPUT_TYPE_SOC
from custom_components.haeo.model.node import NODE_POWER_BALANCE
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.schema import Default
from custom_components.haeo.schema.fields import (
    BatterySOCSensorFieldData,
    BatterySOCSensorFieldSchema,
    ElementNameFieldSchema,
    EnergySensorFieldData,
    EnergySensorFieldSchema,
    NameFieldData,
    NameFieldSchema,
    PercentageSensorFieldData,
    PercentageSensorFieldSchema,
    PowerSensorFieldData,
    PowerSensorFieldSchema,
    PriceFieldData,
    PriceFieldSchema,
    PriceSensorsFieldData,
    PriceSensorsFieldSchema,
)

ELEMENT_TYPE: Final = "battery"

# Field type aliases with defaults
EarlyChargeIncentiveFieldSchema = Annotated[PriceFieldSchema, Default(schema=0.001)]
EarlyChargeIncentiveFieldData = Annotated[PriceFieldData, Default(schema=0.001)]

type BatteryDeviceName = Literal[
    "battery",
    "battery_device_undercharge",
    "battery_device_normal",
    "battery_device_overcharge",
]

BATTERY_DEVICE_NAMES: Final[frozenset[BatteryDeviceName]] = frozenset(
    (
        BATTERY_DEVICE_BATTERY := ELEMENT_TYPE,
        BATTERY_DEVICE_UNDERCHARGE := "battery_device_undercharge",
        BATTERY_DEVICE_NORMAL := "battery_device_normal",
        BATTERY_DEVICE_OVERCHARGE := "battery_device_overcharge",
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

type BatteryOutputName = Literal[
    "battery_power_charge",
    "battery_power_discharge",
    "battery_power_active",
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
        BATTERY_POWER_CHARGE := "battery_power_charge",
        BATTERY_POWER_DISCHARGE := "battery_power_discharge",
        BATTERY_POWER_ACTIVE := "battery_power_active",
        BATTERY_ENERGY_STORED := "battery_energy_stored",
        BATTERY_STATE_OF_CHARGE := "battery_state_of_charge",
        BATTERY_POWER_BALANCE := "battery_power_balance",
        BATTERY_CHARGE_PRICE := "battery_charge_price",
        BATTERY_DISCHARGE_PRICE := "battery_discharge_price",
        BATTERY_ENERGY_IN_FLOW := "battery_energy_in_flow",
        BATTERY_ENERGY_OUT_FLOW := "battery_energy_out_flow",
        BATTERY_SOC_MAX := "battery_soc_max",
        BATTERY_SOC_MIN := "battery_soc_min",
    )
)


class BatteryConfigSchema(TypedDict):
    """Battery configuration with sensor entity IDs."""

    element_type: Literal["battery"]
    name: NameFieldSchema
    connection: ElementNameFieldSchema  # Connection ID that battery connects to
    capacity: EnergySensorFieldSchema
    initial_charge_percentage: BatterySOCSensorFieldSchema
    min_charge_percentage: BatterySOCSensorFieldSchema
    max_charge_percentage: BatterySOCSensorFieldSchema
    efficiency: PercentageSensorFieldSchema
    max_charge_power: NotRequired[PowerSensorFieldSchema]
    max_discharge_power: NotRequired[PowerSensorFieldSchema]
    early_charge_incentive: NotRequired[EarlyChargeIncentiveFieldSchema]
    discharge_cost: NotRequired[PriceSensorsFieldSchema]
    undercharge_percentage: NotRequired[BatterySOCSensorFieldSchema]
    overcharge_percentage: NotRequired[BatterySOCSensorFieldSchema]
    undercharge_cost: NotRequired[PriceSensorsFieldSchema]
    overcharge_cost: NotRequired[PriceSensorsFieldSchema]


class BatteryConfigData(TypedDict):
    """Battery configuration with loaded sensor values."""

    element_type: Literal["battery"]
    name: NameFieldData
    connection: ElementNameFieldSchema  # Connection ID that battery connects to
    capacity: EnergySensorFieldData
    initial_charge_percentage: BatterySOCSensorFieldData
    min_charge_percentage: BatterySOCSensorFieldData
    max_charge_percentage: BatterySOCSensorFieldData
    efficiency: PercentageSensorFieldData
    max_charge_power: NotRequired[PowerSensorFieldData]
    max_discharge_power: NotRequired[PowerSensorFieldData]
    early_charge_incentive: NotRequired[EarlyChargeIncentiveFieldData]
    discharge_cost: NotRequired[PriceSensorsFieldData]
    undercharge_percentage: NotRequired[BatterySOCSensorFieldData]
    overcharge_percentage: NotRequired[BatterySOCSensorFieldData]
    undercharge_cost: NotRequired[PriceSensorsFieldData]
    overcharge_cost: NotRequired[PriceSensorsFieldData]


def create_model_elements(config: BatteryConfigData) -> list[dict[str, Any]]:
    """Create model elements for Battery configuration.

    Creates 1-3 battery sections, an internal node, connections from sections to node,
    and a connection from node to target.
    """
    name = config["name"]
    elements: list[dict[str, Any]] = []

    # Get capacity and initial SOC from first period
    capacity = config["capacity"][0]
    initial_soc = config["initial_charge_percentage"][0]

    # Convert percentages to ratios (take first value if list)
    min_ratio = config["min_charge_percentage"][0] / 100.0
    max_ratio = config["max_charge_percentage"][0] / 100.0
    undercharge_percentage = config.get("undercharge_percentage")
    undercharge_ratio = undercharge_percentage[0] / 100.0 if undercharge_percentage is not None else None
    overcharge_percentage = config.get("overcharge_percentage")
    overcharge_ratio = overcharge_percentage[0] / 100.0 if overcharge_percentage is not None else None
    initial_soc_ratio = initial_soc / 100.0

    # Calculate early charge/discharge incentives - default from EarlyChargeIncentiveFieldSchema
    early_charge_incentive: float = config.get("early_charge_incentive", 0.001)

    # Determine unusable ratio (inaccessible energy)
    unusable_ratio = undercharge_ratio if undercharge_ratio is not None else min_ratio

    # Calculate initial charge in kWh (remove unusable percentage)
    initial_charge = max((initial_soc_ratio - unusable_ratio) * capacity, 0.0)

    # Create battery sections
    section_names: list[str] = []

    # 1. Undercharge section (if configured)
    if undercharge_ratio is not None and config.get("undercharge_cost") is not None:
        section_name = f"{name}:undercharge"
        section_names.append(section_name)
        undercharge_capacity = (min_ratio - undercharge_ratio) * capacity
        section_initial_charge = min(initial_charge, undercharge_capacity)

        elements.append(
            {
                "element_type": "battery",
                "name": section_name,
                "capacity": undercharge_capacity,
                "initial_charge": section_initial_charge,
            }
        )

        initial_charge = max(initial_charge - section_initial_charge, 0.0)

    # 2. Normal section (always present)
    section_name = f"{name}:normal"
    section_names.append(section_name)
    normal_capacity = (max_ratio - min_ratio) * capacity
    section_initial_charge = min(initial_charge, normal_capacity)

    elements.append(
        {
            "element_type": "battery",
            "name": section_name,
            "capacity": normal_capacity,
            "initial_charge": section_initial_charge,
        }
    )

    initial_charge = max(initial_charge - section_initial_charge, 0.0)

    # 3. Overcharge section (if configured)
    if overcharge_ratio is not None and config.get("overcharge_cost") is not None:
        section_name = f"{name}:overcharge"
        section_names.append(section_name)
        overcharge_capacity = (overcharge_ratio - max_ratio) * capacity
        section_initial_charge = min(initial_charge, overcharge_capacity)

        elements.append(
            {
                "element_type": "battery",
                "name": section_name,
                "capacity": overcharge_capacity,
                "initial_charge": section_initial_charge,
            }
        )

    # 4. Create internal node
    node_name = f"{name}:node"
    elements.append(
        {
            "element_type": "node",
            "name": node_name,
            "is_source": False,
            "is_sink": False,
        }
    )

    # 5. Create connections from sections to internal node
    n_periods = len(config["capacity"])

    # Create time-varying early charge/discharge incentive arrays using linspace
    # Charge incentive decreases over time (from -incentive to 0)
    # Discharge cost increases over time (from incentive to 2*incentive)
    charge_early_incentive = [
        -early_charge_incentive + (early_charge_incentive * i / max(n_periods - 1, 1)) for i in range(n_periods)
    ]
    discharge_early_incentive = [
        early_charge_incentive + (early_charge_incentive * i / max(n_periods - 1, 1)) for i in range(n_periods)
    ]

    # Get undercharge/overcharge cost arrays (or broadcast scalars to arrays)
    undercharge_cost_array: list[float] = (
        list(config["undercharge_cost"]) if "undercharge_cost" in config else [0.0] * n_periods
    )
    overcharge_cost_array: list[float] = (
        list(config["overcharge_cost"]) if "overcharge_cost" in config else [0.0] * n_periods
    )

    for section_name in section_names:
        # Determine charge/discharge costs based on section
        if "undercharge" in section_name:
            # Undercharge: strong charge preference (3x), weak discharge + penalty
            charge_price = [c * 3 for c in charge_early_incentive]
            discharge_price = [
                d * 1 + uc for d, uc in zip(discharge_early_incentive, undercharge_cost_array, strict=True)
            ]
        elif "overcharge" in section_name:
            # Overcharge: weak charge + penalty, strong discharge preference (3x)
            charge_price = [c * 1 + oc for c, oc in zip(charge_early_incentive, overcharge_cost_array, strict=True)]
            discharge_price = [d * 3 for d in discharge_early_incentive]
        else:
            # Normal: moderate preferences (2x)
            charge_price = [c * 2 for c in charge_early_incentive]
            discharge_price = [d * 2 for d in discharge_early_incentive]

        elements.append(
            {
                "element_type": "connection",
                "name": f"{section_name}:to_node",
                "source": section_name,
                "target": node_name,
                "price_target_source": charge_price,  # Charging cost (node to section)
                "price_source_target": discharge_price,  # Discharging cost (section to node)
            }
        )

    # 6. Create connection from internal node to target
    elements.append(
        {
            "element_type": "connection",
            "name": f"{name}:connection",
            "source": node_name,
            "target": config["connection"],
            "efficiency_source_target": config["efficiency"],  # Node to network (discharge)
            "efficiency_target_source": config["efficiency"],  # Network to node (charge)
            "max_power_source_target": config.get("max_discharge_power"),
            "max_power_target_source": config.get("max_charge_power"),
            "price_source_target": config.get("discharge_cost"),  # Discharge cost (degradation)
        }
    )

    return elements


def outputs(
    name: str,
    outputs: Mapping[str, Mapping[ModelOutputName, OutputData]],
    config: BatteryConfigData,
) -> Mapping[BatteryDeviceName, Mapping[BatteryOutputName, OutputData]]:
    """Provide state updates for battery output sensors."""
    # Collect section outputs
    section_outputs: dict[str, Mapping[ModelOutputName, OutputData]] = {}
    section_names: list[str] = []

    # Check for undercharge section
    undercharge_name = f"{name}:undercharge"
    if undercharge_name in outputs:
        section_outputs["undercharge"] = outputs[undercharge_name]
        section_names.append("undercharge")

    # Normal section (always present)
    normal_name = f"{name}:normal"
    if normal_name in outputs:
        section_outputs["normal"] = outputs[normal_name]
        section_names.append("normal")

    # Check for overcharge section
    overcharge_name = f"{name}:overcharge"
    if overcharge_name in outputs:
        section_outputs["overcharge"] = outputs[overcharge_name]
        section_names.append("overcharge")

    # Get node outputs for power balance
    node_name = f"{name}:node"
    node_outputs = outputs.get(node_name, {})

    # Calculate aggregate outputs
    # Sum power charge/discharge across all sections
    all_power_charge = [section[model_battery.BATTERY_POWER_CHARGE] for section in section_outputs.values()]
    all_power_discharge = [section[model_battery.BATTERY_POWER_DISCHARGE] for section in section_outputs.values()]

    # Sum energy stored across all sections
    all_energy_stored = [section[model_battery.BATTERY_ENERGY_STORED] for section in section_outputs.values()]

    # Aggregate power values
    aggregate_power_charge = _sum_output_data(all_power_charge)
    aggregate_power_discharge = _sum_output_data(all_power_discharge)
    aggregate_energy_stored = _sum_output_data(all_energy_stored)

    # Calculate total energy stored (including inaccessible energy below min SOC)
    total_energy_stored = _calculate_total_energy(aggregate_energy_stored, config)

    # Calculate SOC from aggregate energy using capacity from config
    aggregate_soc = _calculate_soc(total_energy_stored, config)

    # Build aggregate device outputs
    aggregate_outputs: dict[BatteryOutputName, OutputData] = {
        BATTERY_POWER_CHARGE: aggregate_power_charge,
        BATTERY_POWER_DISCHARGE: aggregate_power_discharge,
        BATTERY_ENERGY_STORED: total_energy_stored,
        BATTERY_STATE_OF_CHARGE: aggregate_soc,
    }

    # Active battery power (discharge - charge)
    aggregate_outputs[BATTERY_POWER_ACTIVE] = replace(
        aggregate_power_discharge,
        values=[
            d - c
            for d, c in zip(
                aggregate_power_discharge.values,
                aggregate_power_charge.values,
                strict=True,
            )
        ],
        direction=None,
        type=OUTPUT_TYPE_POWER,
    )

    # Add node power balance as battery power balance
    if NODE_POWER_BALANCE in node_outputs:
        aggregate_outputs[BATTERY_POWER_BALANCE] = node_outputs[NODE_POWER_BALANCE]

    result: dict[BatteryDeviceName, dict[BatteryOutputName, OutputData]] = {BATTERY_DEVICE_BATTERY: aggregate_outputs}

    # Calculate section-specific prices from config (same logic as create_model_elements)
    n_periods = len(config["capacity"])
    early_charge_incentive = config.get("early_charge_incentive", 0.001)

    charge_early_incentive = [
        -early_charge_incentive + (early_charge_incentive * i / max(n_periods - 1, 1)) for i in range(n_periods)
    ]
    discharge_early_incentive = [
        early_charge_incentive + (early_charge_incentive * i / max(n_periods - 1, 1)) for i in range(n_periods)
    ]

    undercharge_cost_array: list[float] = (
        list(config["undercharge_cost"]) if "undercharge_cost" in config else [0.0] * n_periods
    )
    overcharge_cost_array: list[float] = (
        list(config["overcharge_cost"]) if "overcharge_cost" in config else [0.0] * n_periods
    )

    def get_section_prices(section_key: str) -> tuple[list[float], list[float]]:
        """Get charge and discharge prices for a battery section."""
        if section_key == "undercharge":
            charge_price = [c * 3 for c in charge_early_incentive]
            discharge_price = [
                d * 1 + uc for d, uc in zip(discharge_early_incentive, undercharge_cost_array, strict=True)
            ]
        elif section_key == "overcharge":
            charge_price = [c * 1 + oc for c, oc in zip(charge_early_incentive, overcharge_cost_array, strict=True)]
            discharge_price = [d * 3 for d in discharge_early_incentive]
        else:  # normal
            charge_price = [c * 2 for c in charge_early_incentive]
            discharge_price = [d * 2 for d in discharge_early_incentive]
        return charge_price, discharge_price

    # Add section-specific device outputs
    for section_key in section_names:
        section_data = section_outputs[section_key]
        charge_price, discharge_price = get_section_prices(section_key)

        section_device_outputs: dict[BatteryOutputName, OutputData] = {
            BATTERY_ENERGY_STORED: replace(section_data[model_battery.BATTERY_ENERGY_STORED], advanced=True),
            BATTERY_POWER_CHARGE: replace(section_data[model_battery.BATTERY_POWER_CHARGE], advanced=True),
            BATTERY_POWER_DISCHARGE: replace(section_data[model_battery.BATTERY_POWER_DISCHARGE], advanced=True),
            BATTERY_ENERGY_IN_FLOW: replace(section_data[model_battery.BATTERY_ENERGY_IN_FLOW], advanced=True),
            BATTERY_ENERGY_OUT_FLOW: replace(section_data[model_battery.BATTERY_ENERGY_OUT_FLOW], advanced=True),
            BATTERY_SOC_MAX: replace(section_data[model_battery.BATTERY_SOC_MAX], advanced=True),
            BATTERY_SOC_MIN: replace(section_data[model_battery.BATTERY_SOC_MIN], advanced=True),
            BATTERY_CHARGE_PRICE: OutputData(
                type=OUTPUT_TYPE_PRICE,
                unit="$/kWh",
                values=tuple(charge_price),
                direction="-",
                advanced=True,
            ),
            BATTERY_DISCHARGE_PRICE: OutputData(
                type=OUTPUT_TYPE_PRICE,
                unit="$/kWh",
                values=tuple(discharge_price),
                direction="+",
                advanced=True,
            ),
        }

        # Map to device name
        if section_key == "undercharge":
            result[BATTERY_DEVICE_UNDERCHARGE] = section_device_outputs
        elif section_key == "normal":
            result[BATTERY_DEVICE_NORMAL] = section_device_outputs
        elif section_key == "overcharge":
            result[BATTERY_DEVICE_OVERCHARGE] = section_device_outputs

    return result


def _sum_output_data(outputs: list[OutputData]) -> OutputData:
    """Sum multiple OutputData objects."""
    if not outputs:
        msg = "Cannot sum empty list of outputs"
        raise ValueError(msg)

    first = outputs[0]
    summed_values = np.sum([o.values for o in outputs], axis=0)

    return OutputData(
        type=first.type,
        unit=first.unit,
        values=tuple(summed_values.tolist()),
        direction=first.direction,
        advanced=first.advanced,
    )


def _calculate_total_energy(aggregate_energy: OutputData, config: BatteryConfigData) -> OutputData:
    """Calculate total energy stored including inaccessible energy below min SOC."""
    capacity = np.array(config["capacity"])

    min_ratio = config["min_charge_percentage"][0] / 100.0
    undercharge_percentage = config.get("undercharge_percentage")
    undercharge_ratio = undercharge_percentage[0] / 100.0 if undercharge_percentage is not None else None
    unusable_ratio = undercharge_ratio if undercharge_ratio is not None else min_ratio

    # Fence-post: energy has n+1 values, capacity has n periods
    # Use preceding capacity for each energy point (first uses first capacity)
    fence_post_capacity = np.concatenate([[capacity[0]], capacity])
    inaccessible_energy = unusable_ratio * fence_post_capacity
    total_values = np.array(aggregate_energy.values) + inaccessible_energy

    return OutputData(
        type=aggregate_energy.type,
        unit=aggregate_energy.unit,
        values=tuple(total_values.tolist()),
    )


def _calculate_soc(total_energy: OutputData, config: BatteryConfigData) -> OutputData:
    """Calculate SOC percentage from aggregate energy and total capacity."""
    capacity = np.array(config["capacity"])

    # Fence-post: energy has n+1 values, capacity has n periods
    # Use preceding capacity for each SOC point (first uses first capacity)
    fence_post_capacity = np.concatenate([[capacity[0]], capacity])
    soc_values = np.array(total_energy.values) / fence_post_capacity * 100.0

    return OutputData(
        type=OUTPUT_TYPE_SOC,
        unit="%",
        values=tuple(soc_values.tolist()),
    )
