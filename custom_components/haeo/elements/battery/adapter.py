"""Battery element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.core import HomeAssistant
import numpy as np

from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model import battery as model_battery
from custom_components.haeo.model import battery_balance_connection as model_balance
from custom_components.haeo.model import power_connection as model_connection
from custom_components.haeo.model.const import OUTPUT_TYPE_POWER, OUTPUT_TYPE_POWER_FLOW, OUTPUT_TYPE_SOC
from custom_components.haeo.model.node import NODE_POWER_BALANCE
from custom_components.haeo.model.output_data import OutputData

from .flow import BatterySubentryFlowHandler
from .schema import (
    CONF_CAPACITY,
    CONF_CONNECTION,
    CONF_DISCHARGE_COST,
    CONF_EARLY_CHARGE_INCENTIVE,
    CONF_EFFICIENCY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_POWER,
    CONF_MAX_DISCHARGE_POWER,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_OVERCHARGE_COST,
    CONF_OVERCHARGE_PERCENTAGE,
    CONF_UNDERCHARGE_COST,
    CONF_UNDERCHARGE_PERCENTAGE,
    DEFAULTS,
    ELEMENT_TYPE,
    BatteryConfigData,
    BatteryConfigSchema,
)

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
    "battery_balance_power_down",
    "battery_balance_power_up",
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
        BATTERY_BALANCE_POWER_DOWN := "battery_balance_power_down",
        BATTERY_BALANCE_POWER_UP := "battery_balance_power_up",
    )
)

type BatteryDeviceName = Literal[
    "battery",
    "battery_device_undercharge",
    "battery_device_normal",
    "battery_device_overcharge",
]

BATTERY_DEVICE_NAMES: Final[frozenset[BatteryDeviceName]] = frozenset(
    (
        BATTERY_DEVICE_BATTERY := "battery",
        BATTERY_DEVICE_UNDERCHARGE := "battery_device_undercharge",
        BATTERY_DEVICE_NORMAL := "battery_device_normal",
        BATTERY_DEVICE_OVERCHARGE := "battery_device_overcharge",
    )
)


class BatteryAdapter:
    """Adapter for Battery elements."""

    element_type: str = ELEMENT_TYPE
    flow_class: type = BatterySubentryFlowHandler
    advanced: bool = False
    connectivity: str = "advanced"

    def available(self, config: BatteryConfigSchema, *, hass: HomeAssistant, **_kwargs: Any) -> bool:
        """Check if battery configuration can be loaded."""
        ts_loader = TimeSeriesLoader()

        # Check required time series fields
        required_fields = [CONF_CAPACITY, CONF_INITIAL_CHARGE_PERCENTAGE]
        for field in required_fields:
            if not ts_loader.available(hass=hass, value=config[field]):
                return False

        # Check optional time series fields if present
        optional_ts_fields = [
            CONF_MAX_CHARGE_POWER,
            CONF_MAX_DISCHARGE_POWER,
            CONF_DISCHARGE_COST,
            CONF_UNDERCHARGE_COST,
            CONF_OVERCHARGE_COST,
        ]
        for field in optional_ts_fields:
            if field in config and not ts_loader.available(hass=hass, value=config[field]):
                return False

        return True

    async def load(
        self,
        config: BatteryConfigSchema,
        *,
        hass: HomeAssistant,
        forecast_times: Sequence[float],
    ) -> BatteryConfigData:
        """Load battery configuration values from sensors."""
        ts_loader = TimeSeriesLoader()

        # Load required time series
        capacity = await ts_loader.load(hass=hass, value=config[CONF_CAPACITY], forecast_times=forecast_times)
        initial_charge = await ts_loader.load(
            hass=hass, value=config[CONF_INITIAL_CHARGE_PERCENTAGE], forecast_times=forecast_times
        )

        # Build data with defaults applied
        data: BatteryConfigData = {
            "element_type": config["element_type"],
            "name": config["name"],
            "connection": config[CONF_CONNECTION],
            "capacity": capacity,
            "initial_charge_percentage": initial_charge,
            "min_charge_percentage": config.get(CONF_MIN_CHARGE_PERCENTAGE, DEFAULTS[CONF_MIN_CHARGE_PERCENTAGE]),
            "max_charge_percentage": config.get(CONF_MAX_CHARGE_PERCENTAGE, DEFAULTS[CONF_MAX_CHARGE_PERCENTAGE]),
            "efficiency": config.get(CONF_EFFICIENCY, DEFAULTS[CONF_EFFICIENCY]),
        }

        # Load optional time series fields
        if CONF_MAX_CHARGE_POWER in config:
            data["max_charge_power"] = await ts_loader.load(
                hass=hass, value=config[CONF_MAX_CHARGE_POWER], forecast_times=forecast_times
            )
        if CONF_MAX_DISCHARGE_POWER in config:
            data["max_discharge_power"] = await ts_loader.load(
                hass=hass, value=config[CONF_MAX_DISCHARGE_POWER], forecast_times=forecast_times
            )
        if CONF_DISCHARGE_COST in config:
            data["discharge_cost"] = await ts_loader.load(
                hass=hass, value=config[CONF_DISCHARGE_COST], forecast_times=forecast_times
            )

        # Load optional scalars
        if CONF_EARLY_CHARGE_INCENTIVE in config:
            data["early_charge_incentive"] = config[CONF_EARLY_CHARGE_INCENTIVE]
        if CONF_UNDERCHARGE_PERCENTAGE in config:
            data["undercharge_percentage"] = config[CONF_UNDERCHARGE_PERCENTAGE]
        if CONF_OVERCHARGE_PERCENTAGE in config:
            data["overcharge_percentage"] = config[CONF_OVERCHARGE_PERCENTAGE]

        # Load optional undercharge/overcharge costs
        if CONF_UNDERCHARGE_COST in config:
            data["undercharge_cost"] = await ts_loader.load(
                hass=hass, value=config[CONF_UNDERCHARGE_COST], forecast_times=forecast_times
            )
        if CONF_OVERCHARGE_COST in config:
            data["overcharge_cost"] = await ts_loader.load(
                hass=hass, value=config[CONF_OVERCHARGE_COST], forecast_times=forecast_times
            )

        return data

    def create_model_elements(self, config: BatteryConfigData) -> list[dict[str, Any]]:
        """Create model elements for Battery configuration.

        Creates 1-3 battery sections, an internal node, connections from sections to node,
        and a connection from node to target.

        When required_energy is provided (blackout protection), the undercharge section
        capacity is set dynamically per-timestep to match the required energy for
        blackout survival. The undercharge_cost mechanism makes discharging from this
        section expensive, naturally keeping it charged.
        """
        name = config["name"]
        elements: list[dict[str, Any]] = []

        # Get capacity and initial SOC from first period
        capacity = config["capacity"][0]
        initial_soc = config["initial_charge_percentage"][0]

        # Convert percentages to ratios
        min_ratio = config["min_charge_percentage"] / 100.0
        max_ratio = config["max_charge_percentage"] / 100.0
        overcharge_ratio = (
            config.get("overcharge_percentage", max_ratio) / 100.0 if config.get("overcharge_percentage") else None
        )
        initial_soc_ratio = initial_soc / 100.0

        # Calculate early charge/discharge incentives
        early_charge_incentive = config.get("early_charge_incentive", DEFAULTS[CONF_EARLY_CHARGE_INCENTIVE])

        # Check if dynamic undercharge sizing is enabled (required_energy provided)
        required_energy = config.get("required_energy")
        has_dynamic_undercharge = required_energy is not None and config.get("undercharge_cost") is not None

        # Determine undercharge ratio for static mode (when no required_energy)
        undercharge_ratio = (
            config.get("undercharge_percentage", min_ratio) / 100.0 if config.get("undercharge_percentage") else None
        )

        # Determine unusable ratio (inaccessible energy)
        # For dynamic mode, use min_ratio as the base (required_energy extends below it)
        # For static mode, use undercharge_ratio if set
        if has_dynamic_undercharge:
            unusable_ratio = min_ratio
        else:
            unusable_ratio = undercharge_ratio if undercharge_ratio is not None else min_ratio

        # Calculate initial charge in kWh (remove unusable percentage)
        initial_charge = max((initial_soc_ratio - unusable_ratio) * capacity, 0.0)

        # Create battery sections
        section_names: list[str] = []

        # Track dynamic undercharge capacity for normal section sizing
        dynamic_undercharge_capacity: list[float] | None = None

        # 1. Undercharge section (dynamic or static)
        if has_dynamic_undercharge and required_energy is not None:
            # Dynamic mode: undercharge capacity = required_energy per timestep
            # required_energy has n_periods + 1 values (fence-post for energy boundaries)
            section_name = f"{name}:undercharge"
            section_names.append(section_name)

            # Use required_energy directly as per-timestep capacity
            # Cap each value at the total battery capacity to ensure feasibility
            # The BatteryBalanceConnection handles excess energy when capacity shrinks
            undercharge_capacity: list[float] = [min(re, capacity) for re in required_energy]

            # Store for normal section calculation
            dynamic_undercharge_capacity = undercharge_capacity

            # Initial charge for undercharge section: how much of current charge fits in undercharge
            section_initial_charge = min(initial_charge, undercharge_capacity[0])

            elements.append(
                {
                    "element_type": "battery",
                    "name": section_name,
                    "capacity": undercharge_capacity,
                    "initial_charge": section_initial_charge,
                }
            )

            initial_charge = max(initial_charge - section_initial_charge, 0.0)

        elif undercharge_ratio is not None and config.get("undercharge_cost") is not None:
            # Static mode: undercharge capacity based on percentage
            section_name = f"{name}:undercharge"
            section_names.append(section_name)
            static_undercharge_capacity = (min_ratio - undercharge_ratio) * capacity
            section_initial_charge = min(initial_charge, static_undercharge_capacity)

            elements.append(
                {
                    "element_type": "battery",
                    "name": section_name,
                    "capacity": static_undercharge_capacity,
                    "initial_charge": section_initial_charge,
                }
            )

            initial_charge = max(initial_charge - section_initial_charge, 0.0)

        # 2. Normal section (always present)
        # For dynamic undercharge mode, normal section gets remaining capacity after undercharge
        # For static mode, normal section gets (max_ratio - min_ratio) * capacity
        section_name = f"{name}:normal"
        section_names.append(section_name)

        # Calculate base normal capacity
        base_normal_capacity = (max_ratio - min_ratio) * capacity

        if has_dynamic_undercharge and dynamic_undercharge_capacity is not None:
            # Dynamic mode: normal capacity = total accessible capacity - undercharge capacity
            # dynamic_undercharge_capacity is a list; normal gets remaining capacity at each timestep
            normal_capacity_values = [max(base_normal_capacity - uc, 0.0) for uc in dynamic_undercharge_capacity]
            normal_capacity: float | list[float] = normal_capacity_values
            section_initial_charge = min(initial_charge, normal_capacity_values[0])
        else:
            # Static mode: normal section gets full (max_ratio - min_ratio) * capacity
            normal_capacity = base_normal_capacity
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

        # 4. Create balance connection for dynamic undercharge mode
        # This allows free energy transfer between undercharge and normal sections
        # when undercharge capacity shrinks (required_energy decreases as solar arrives)
        if has_dynamic_undercharge and dynamic_undercharge_capacity is not None:
            undercharge_section_name = f"{name}:undercharge"
            normal_section_name = f"{name}:normal"
            elements.append(
                {
                    "element_type": "battery_balance_connection",
                    "name": f"{name}:balance:undercharge:normal",
                    "upper": normal_section_name,
                    "lower": undercharge_section_name,
                    "capacity_lower": dynamic_undercharge_capacity,
                }
            )

        # 5. Create internal node
        node_name = f"{name}:node"
        elements.append(
            {
                "element_type": "node",
                "name": node_name,
                "is_source": False,
                "is_sink": False,
            }
        )

        # 6. Create connections from sections to internal node
        n_periods = len(config["capacity"])

        # Get undercharge/overcharge cost arrays (or broadcast scalars to arrays)
        undercharge_cost_array: list[float] = (
            list(config["undercharge_cost"]) if "undercharge_cost" in config else [0.0] * n_periods
        )
        overcharge_cost_array: list[float] = (
            list(config["overcharge_cost"]) if "overcharge_cost" in config else [0.0] * n_periods
        )

        for section_name in section_names:
            # Determine discharge costs based on section (undercharge/overcharge penalties)
            # Ordering is enforced by balance connections, not price incentives
            if "undercharge" in section_name:
                discharge_price = undercharge_cost_array
            elif "overcharge" in section_name:
                charge_price: list[float] = overcharge_cost_array
                elements.append(
                    {
                        "element_type": "connection",
                        "name": f"{section_name}:to_node",
                        "source": section_name,
                        "target": node_name,
                        "price_target_source": charge_price,  # Overcharge penalty when charging
                    }
                )
                continue
            else:
                discharge_price = None

            elements.append(
                {
                    "element_type": "connection",
                    "name": f"{section_name}:to_node",
                    "source": section_name,
                    "target": node_name,
                    "price_source_target": discharge_price,  # Undercharge penalty when discharging
                }
            )

        # 6b. Create balance connections between adjacent sections (enforces fill ordering)
        # Balance connections ensure lower sections fill before upper sections
        # Skip if dynamic undercharge balance connection already created in step 4
        section_capacities: dict[str, float] = {}
        for section_name in section_names:
            if "undercharge" in section_name:
                # Static undercharge capacity from undercharge_percentage, or skip if dynamic
                if undercharge_ratio is not None:
                    section_capacities[section_name] = (min_ratio - undercharge_ratio) * capacity  # type: ignore[operator]
                # Dynamic undercharge handled in step 4 - no need to set capacity here
            elif "overcharge" in section_name:
                if overcharge_ratio is not None:
                    section_capacities[section_name] = (overcharge_ratio - max_ratio) * capacity  # type: ignore[operator]
            else:
                section_capacities[section_name] = normal_capacity

        for i in range(len(section_names) - 1):
            lower_section = section_names[i]
            upper_section = section_names[i + 1]

            # Skip if already created dynamic balance connection in step 4
            if has_dynamic_undercharge and "undercharge" in lower_section and "normal" in upper_section:
                continue

            # Skip if capacity not computed (e.g., dynamic undercharge without static ratio)
            if lower_section not in section_capacities:
                continue

            lower_capacity = section_capacities[lower_section]
            elements.append(
                {
                    "element_type": "battery_balance_connection",
                    "name": f"{name}:balance:{lower_section.split(':')[-1]}:{upper_section.split(':')[-1]}",
                    "upper": upper_section,
                    "lower": lower_section,
                    "capacity_lower": lower_capacity,
                }
            )

        # 7. Create connection from internal node to target
        # Time-varying early charge incentive applied here (charge earlier in horizon)
        charge_early_incentive = [
            -early_charge_incentive + (early_charge_incentive * i / max(n_periods - 1, 1)) for i in range(n_periods)
        ]
        discharge_early_incentive = [
            early_charge_incentive + (early_charge_incentive * i / max(n_periods - 1, 1)) for i in range(n_periods)
        ]

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
                "price_target_source": charge_early_incentive,  # Charge early incentive
                "price_source_target": (
                    [d + dc for d, dc in zip(discharge_early_incentive, config["discharge_cost"], strict=True)]
                    if "discharge_cost" in config
                    else discharge_early_incentive
                ),  # Discharge cost + early incentive
            }
        )

        return elements

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]],
        _config: BatteryConfigData,
    ) -> Mapping[BatteryDeviceName, Mapping[BatteryOutputName, OutputData]]:
        """Map model outputs to battery-specific output names.

        Aggregates outputs from multiple battery sections and connections.
        Returns multiple devices for SOC regions based on what's configured.
        """
        # Collect section outputs
        section_outputs: dict[str, Mapping[ModelOutputName, OutputData]] = {}
        section_names: list[str] = []

        # Check for undercharge section
        undercharge_name = f"{name}:undercharge"
        if undercharge_name in model_outputs:
            section_outputs["undercharge"] = model_outputs[undercharge_name]
            section_names.append("undercharge")

        # Normal section (always present)
        normal_name = f"{name}:normal"
        if normal_name in model_outputs:
            section_outputs["normal"] = model_outputs[normal_name]
            section_names.append("normal")

        # Check for overcharge section
        overcharge_name = f"{name}:overcharge"
        if overcharge_name in model_outputs:
            section_outputs["overcharge"] = model_outputs[overcharge_name]
            section_names.append("overcharge")

        # Get node outputs for power balance
        node_name = f"{name}:node"
        node_outputs = model_outputs.get(node_name, {})

        # Get connection outputs for prices
        connection_outputs: dict[str, Mapping[ModelOutputName, OutputData]] = {}
        for section_key in section_names:
            section_full_name = f"{name}:{section_key}"
            conn_name = f"{section_full_name}:to_node"
            if conn_name in model_outputs:
                connection_outputs[section_key] = model_outputs[conn_name]

        # Calculate aggregate outputs
        # Sum power charge/discharge across all sections
        all_power_charge = [section[model_battery.BATTERY_POWER_CHARGE] for section in section_outputs.values()]
        all_power_discharge = [section[model_battery.BATTERY_POWER_DISCHARGE] for section in section_outputs.values()]

        # Sum energy stored across all sections
        all_energy_stored = [section[model_battery.BATTERY_ENERGY_STORED] for section in section_outputs.values()]

        # Aggregate power values
        aggregate_power_charge = sum_output_data(all_power_charge)
        aggregate_power_discharge = sum_output_data(all_power_discharge)
        aggregate_energy_stored = sum_output_data(all_energy_stored)

        # Calculate total energy stored (including inaccessible energy below min SOC)
        total_energy_stored = _calculate_total_energy(aggregate_energy_stored, _config)

        # Calculate SOC from aggregate energy using capacity from config
        aggregate_soc = _calculate_soc(total_energy_stored, _config)

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

        result: dict[BatteryDeviceName, dict[BatteryOutputName, OutputData]] = {
            BATTERY_DEVICE_BATTERY: aggregate_outputs
        }

        # Add section-specific device outputs
        for section_key in section_names:
            section_data = section_outputs[section_key]
            conn_data = connection_outputs.get(section_key, {})

            section_device_outputs: dict[BatteryOutputName, OutputData] = {
                BATTERY_ENERGY_STORED: replace(section_data[model_battery.BATTERY_ENERGY_STORED], advanced=True),
                BATTERY_POWER_CHARGE: replace(section_data[model_battery.BATTERY_POWER_CHARGE], advanced=True),
                BATTERY_POWER_DISCHARGE: replace(section_data[model_battery.BATTERY_POWER_DISCHARGE], advanced=True),
                BATTERY_ENERGY_IN_FLOW: replace(section_data[model_battery.BATTERY_ENERGY_IN_FLOW], advanced=True),
                BATTERY_ENERGY_OUT_FLOW: replace(section_data[model_battery.BATTERY_ENERGY_OUT_FLOW], advanced=True),
                BATTERY_SOC_MAX: replace(section_data[model_battery.BATTERY_SOC_MAX], advanced=True),
                BATTERY_SOC_MIN: replace(section_data[model_battery.BATTERY_SOC_MIN], advanced=True),
            }

            # Add connection prices
            if model_connection.CONNECTION_PRICE_TARGET_SOURCE in conn_data:
                section_device_outputs[BATTERY_CHARGE_PRICE] = replace(
                    conn_data[model_connection.CONNECTION_PRICE_TARGET_SOURCE], advanced=True
                )
            if model_connection.CONNECTION_PRICE_SOURCE_TARGET in conn_data:
                section_device_outputs[BATTERY_DISCHARGE_PRICE] = replace(
                    conn_data[model_connection.CONNECTION_PRICE_SOURCE_TARGET], advanced=True
                )

            # Map to device name
            if section_key == "undercharge":
                result[BATTERY_DEVICE_UNDERCHARGE] = section_device_outputs
            elif section_key == "normal":
                result[BATTERY_DEVICE_NORMAL] = section_device_outputs
            elif section_key == "overcharge":
                result[BATTERY_DEVICE_OVERCHARGE] = section_device_outputs

        # Map section keys to device keys
        section_to_device: dict[str, BatteryDeviceName] = {
            "undercharge": BATTERY_DEVICE_UNDERCHARGE,
            "normal": BATTERY_DEVICE_NORMAL,
            "overcharge": BATTERY_DEVICE_OVERCHARGE,
        }

        # Add balance power outputs to each section device
        # power_down = energy flowing into this section from above
        # power_up = energy flowing out of this section to above
        for i, section_key in enumerate(section_names):
            # Get device for this section - all sections in section_names have corresponding devices
            device_key = section_to_device[section_key]

            # Accumulate power_down and power_up from all adjacent balance connections
            power_down_values: list[float] | None = None
            power_up_values: list[float] | None = None

            # Check for balance connection with section below (this section is upper)
            # In this connection: power_down leaves this section, power_up enters this section
            if i > 0:
                lower_key = section_names[i - 1]
                balance_name = f"{name}:balance:{lower_key}:{section_key}"
                if balance_name in model_outputs:
                    balance_data = model_outputs[balance_name]
                    # Power down from this section to lower section (energy leaving downward)
                    if model_balance.BALANCE_POWER_DOWN in balance_data:
                        down_vals = balance_data[model_balance.BALANCE_POWER_DOWN].values
                        power_down_values = list(down_vals)
                    # Power up from lower section to this section (energy entering from below)
                    if model_balance.BALANCE_POWER_UP in balance_data:
                        up_vals = balance_data[model_balance.BALANCE_POWER_UP].values
                        power_up_values = list(up_vals)

            # Check for balance connection with section above (this section is lower)
            # In this connection: power_down enters this section, power_up leaves this section
            if i < len(section_names) - 1:
                upper_key = section_names[i + 1]
                balance_name = f"{name}:balance:{section_key}:{upper_key}"
                if balance_name in model_outputs:
                    balance_data = model_outputs[balance_name]
                    # Power down from upper section to this section (energy entering from above)
                    if model_balance.BALANCE_POWER_DOWN in balance_data:
                        down_vals = np.array(balance_data[model_balance.BALANCE_POWER_DOWN].values)
                        if power_down_values is None:
                            power_down_values = list(down_vals)
                        else:
                            power_down_values = list(np.array(power_down_values) + down_vals)
                    # Power up from this section to upper section (energy leaving upward)
                    if model_balance.BALANCE_POWER_UP in balance_data:
                        up_vals = np.array(balance_data[model_balance.BALANCE_POWER_UP].values)
                        if power_up_values is None:
                            power_up_values = list(up_vals)
                        else:
                            power_up_values = list(np.array(power_up_values) + up_vals)

            if power_down_values is not None:
                result[device_key][BATTERY_BALANCE_POWER_DOWN] = OutputData(
                    type=OUTPUT_TYPE_POWER_FLOW,
                    unit="kW",
                    values=tuple(float(v) for v in power_down_values),
                    advanced=True,
                )
            if power_up_values is not None:
                result[device_key][BATTERY_BALANCE_POWER_UP] = OutputData(
                    type=OUTPUT_TYPE_POWER_FLOW,
                    unit="kW",
                    values=tuple(float(v) for v in power_up_values),
                    advanced=True,
                )

        return result


adapter = BatteryAdapter()


def sum_output_data(outputs: list[OutputData]) -> OutputData:
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

    min_ratio = config["min_charge_percentage"] / 100.0
    undercharge_ratio = (
        config.get("undercharge_percentage", min_ratio) / 100.0 if config.get("undercharge_percentage") else None
    )
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
