"""Battery element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.core import HomeAssistant
import numpy as np

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.model import battery as model_battery
from custom_components.haeo.model import battery_balance_connection as model_balance
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_BATTERY_BALANCE_CONNECTION,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
    SegmentSpec,
)
from custom_components.haeo.model.elements.node import NODE_POWER_BALANCE
from custom_components.haeo.model.elements.segments import (
    EfficiencySegmentSpec,
    PowerLimitSegmentSpec,
    PricingSegmentSpec,
)
from custom_components.haeo.model.output_data import OutputData, require_output_map

from .flow import BatterySubentryFlowHandler
from .schema import (
    CONF_CONNECTION,
    CONF_DISCHARGE_COST,
    CONF_EARLY_CHARGE_INCENTIVE,
    CONF_EFFICIENCY,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_POWER,
    CONF_MAX_DISCHARGE_POWER,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_OVERCHARGE_COST,
    CONF_OVERCHARGE_PERCENTAGE,
    CONF_UNDERCHARGE_COST,
    CONF_UNDERCHARGE_PERCENTAGE,
    ELEMENT_TYPE,
    BatteryConfigData,
    BatteryConfigSchema,
)

# Default values for optional fields applied by adapter
DEFAULTS: Final[dict[str, float]] = {
    CONF_MIN_CHARGE_PERCENTAGE: 0.0,
    CONF_MAX_CHARGE_PERCENTAGE: 100.0,
    CONF_EFFICIENCY: 99.0,
    CONF_EARLY_CHARGE_INCENTIVE: 0.001,
}

type BatteryOutputName = Literal[
    "battery_power_charge",
    "battery_power_discharge",
    "battery_power_active",
    "battery_energy_stored",
    "battery_state_of_charge",
    "battery_power_balance",
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
    connectivity: ConnectivityLevel = ConnectivityLevel.ADVANCED

    def available(self, config: BatteryConfigSchema, *, hass: HomeAssistant, **_kwargs: Any) -> bool:
        """Check if battery configuration can be loaded."""
        ts_loader = TimeSeriesLoader()

        # Helper to check entity availability (handles all config value types)
        def entity_available(value: list[str] | str | float | None) -> bool:
            if value is None or isinstance(value, float | int):
                return True  # Constants and missing values are always available
            if isinstance(value, str):
                return ts_loader.available(hass=hass, value=[value])
            # list[str] for entity chaining
            return ts_loader.available(hass=hass, value=value) if value else True

        # Check required fields
        if not entity_available(config.get("capacity")):
            return False
        if not entity_available(config.get("initial_charge_percentage")):
            return False

        # Check optional time series fields if present
        optional_fields = [
            CONF_MAX_CHARGE_POWER,
            CONF_MAX_DISCHARGE_POWER,
            CONF_DISCHARGE_COST,
            CONF_UNDERCHARGE_COST,
            CONF_OVERCHARGE_COST,
            CONF_MIN_CHARGE_PERCENTAGE,
            CONF_MAX_CHARGE_PERCENTAGE,
            CONF_EFFICIENCY,
            CONF_EARLY_CHARGE_INCENTIVE,
            CONF_UNDERCHARGE_PERCENTAGE,
            CONF_OVERCHARGE_PERCENTAGE,
        ]
        return all(entity_available(config.get(field)) for field in optional_fields)

    def build_config_data(
        self,
        loaded_values: Mapping[str, Any],
        config: BatteryConfigSchema,
    ) -> BatteryConfigData:
        """Build ConfigData from pre-loaded values.

        This is the single source of truth for ConfigData construction.
        Both load() and the coordinator use this method.

        Args:
            loaded_values: Dict of field names to loaded values (from input entities or TimeSeriesLoader)
            config: Original ConfigSchema for non-input fields (element_type, name, connection)

        Returns:
            BatteryConfigData with all fields populated and defaults applied

        """
        # Determine array sizes from capacity (a required boundary field)
        capacity = loaded_values["capacity"]
        n_boundaries = len(capacity)
        n_periods = max(0, n_boundaries - 1)

        # Apply defaults for optional fields with defaults
        min_charge = loaded_values.get(
            CONF_MIN_CHARGE_PERCENTAGE,
            [DEFAULTS[CONF_MIN_CHARGE_PERCENTAGE]] * n_boundaries,
        )
        max_charge = loaded_values.get(
            CONF_MAX_CHARGE_PERCENTAGE,
            [DEFAULTS[CONF_MAX_CHARGE_PERCENTAGE]] * n_boundaries,
        )
        efficiency = loaded_values.get(
            CONF_EFFICIENCY,
            [DEFAULTS[CONF_EFFICIENCY]] * n_periods,
        )

        # Build data with required fields and defaults
        data: BatteryConfigData = {
            "element_type": config["element_type"],
            "name": config["name"],
            "connection": config[CONF_CONNECTION],
            "capacity": list(capacity),
            "initial_charge_percentage": list(loaded_values["initial_charge_percentage"]),
            "min_charge_percentage": list(min_charge),
            "max_charge_percentage": list(max_charge),
            "efficiency": list(efficiency),
        }

        # Optional fields without defaults - only include if present in loaded_values
        if CONF_MAX_CHARGE_POWER in loaded_values:
            data["max_charge_power"] = list(loaded_values[CONF_MAX_CHARGE_POWER])

        if CONF_MAX_DISCHARGE_POWER in loaded_values:
            data["max_discharge_power"] = list(loaded_values[CONF_MAX_DISCHARGE_POWER])

        if CONF_DISCHARGE_COST in loaded_values:
            data["discharge_cost"] = list(loaded_values[CONF_DISCHARGE_COST])

        if CONF_EARLY_CHARGE_INCENTIVE in loaded_values:
            data["early_charge_incentive"] = list(loaded_values[CONF_EARLY_CHARGE_INCENTIVE])

        if CONF_UNDERCHARGE_PERCENTAGE in loaded_values:
            data["undercharge_percentage"] = list(loaded_values[CONF_UNDERCHARGE_PERCENTAGE])

        if CONF_OVERCHARGE_PERCENTAGE in loaded_values:
            data["overcharge_percentage"] = list(loaded_values[CONF_OVERCHARGE_PERCENTAGE])

        if CONF_UNDERCHARGE_COST in loaded_values:
            data["undercharge_cost"] = list(loaded_values[CONF_UNDERCHARGE_COST])

        if CONF_OVERCHARGE_COST in loaded_values:
            data["overcharge_cost"] = list(loaded_values[CONF_OVERCHARGE_COST])

        return data

    async def load(
        self,
        config: BatteryConfigSchema,
        *,
        hass: HomeAssistant,
        forecast_times: Sequence[float],
    ) -> BatteryConfigData:
        """Load battery configuration values from sensors.

        Uses TimeSeriesLoader to load values, then delegates to build_config_data().
        """
        loader = TimeSeriesLoader()
        loaded_values: dict[str, list[float]] = {}

        # Load required fields
        loaded_values["capacity"] = await loader.load_boundaries(
            hass=hass, forecast_times=forecast_times, value=config.get("capacity")
        )
        loaded_values["initial_charge_percentage"] = await loader.load_intervals(
            hass=hass, forecast_times=forecast_times, value=config.get("initial_charge_percentage")
        )

        # Load optional fields with defaults (let build_config_data apply defaults if missing)
        if CONF_MIN_CHARGE_PERCENTAGE in config:
            loaded_values[CONF_MIN_CHARGE_PERCENTAGE] = await loader.load_boundaries(
                hass=hass, forecast_times=forecast_times, value=config[CONF_MIN_CHARGE_PERCENTAGE]
            )
        if CONF_MAX_CHARGE_PERCENTAGE in config:
            loaded_values[CONF_MAX_CHARGE_PERCENTAGE] = await loader.load_boundaries(
                hass=hass, forecast_times=forecast_times, value=config[CONF_MAX_CHARGE_PERCENTAGE]
            )
        if CONF_EFFICIENCY in config:
            loaded_values[CONF_EFFICIENCY] = await loader.load_intervals(
                hass=hass, forecast_times=forecast_times, value=config[CONF_EFFICIENCY]
            )

        # Load optional fields without defaults
        if CONF_MAX_CHARGE_POWER in config:
            loaded_values[CONF_MAX_CHARGE_POWER] = await loader.load_intervals(
                hass=hass, forecast_times=forecast_times, value=config[CONF_MAX_CHARGE_POWER]
            )
        if CONF_MAX_DISCHARGE_POWER in config:
            loaded_values[CONF_MAX_DISCHARGE_POWER] = await loader.load_intervals(
                hass=hass, forecast_times=forecast_times, value=config[CONF_MAX_DISCHARGE_POWER]
            )
        if CONF_DISCHARGE_COST in config:
            loaded_values[CONF_DISCHARGE_COST] = await loader.load_intervals(
                hass=hass, forecast_times=forecast_times, value=config[CONF_DISCHARGE_COST]
            )
        if CONF_EARLY_CHARGE_INCENTIVE in config:
            loaded_values[CONF_EARLY_CHARGE_INCENTIVE] = await loader.load_intervals(
                hass=hass, forecast_times=forecast_times, value=config[CONF_EARLY_CHARGE_INCENTIVE]
            )
        if CONF_UNDERCHARGE_PERCENTAGE in config:
            loaded_values[CONF_UNDERCHARGE_PERCENTAGE] = await loader.load_boundaries(
                hass=hass, forecast_times=forecast_times, value=config[CONF_UNDERCHARGE_PERCENTAGE]
            )
        if CONF_OVERCHARGE_PERCENTAGE in config:
            loaded_values[CONF_OVERCHARGE_PERCENTAGE] = await loader.load_boundaries(
                hass=hass, forecast_times=forecast_times, value=config[CONF_OVERCHARGE_PERCENTAGE]
            )
        if CONF_UNDERCHARGE_COST in config:
            loaded_values[CONF_UNDERCHARGE_COST] = await loader.load_intervals(
                hass=hass, forecast_times=forecast_times, value=config[CONF_UNDERCHARGE_COST]
            )
        if CONF_OVERCHARGE_COST in config:
            loaded_values[CONF_OVERCHARGE_COST] = await loader.load_intervals(
                hass=hass, forecast_times=forecast_times, value=config[CONF_OVERCHARGE_COST]
            )

        return self.build_config_data(loaded_values, config)

    def model_elements(self, config: BatteryConfigData) -> list[ModelElementConfig]:
        """Create model elements for Battery configuration.

        Creates 1-3 battery sections, an internal node, connections from sections to node,
        and a connection from node to target.
        """
        name = config["name"]
        elements: list[ModelElementConfig] = []
        # capacity is boundaries (n+1 values), so n_periods = len - 1
        n_boundaries = len(config["capacity"])
        n_periods = n_boundaries - 1

        # Get capacity array and initial SOC from first period
        capacity_array = np.array(config["capacity"])
        capacity_first = capacity_array[0]
        initial_soc = config["initial_charge_percentage"][0]

        # Convert percentages to ratio arrays for time-varying limits
        min_ratio_array = np.array(config["min_charge_percentage"]) / 100.0
        max_ratio_array = np.array(config["max_charge_percentage"]) / 100.0
        min_ratio_first = min_ratio_array[0]

        # Get optional percentage arrays (if present)
        undercharge_pct = config.get("undercharge_percentage")
        undercharge_ratio_array = np.array(undercharge_pct) / 100.0 if undercharge_pct else None
        undercharge_ratio_first = undercharge_ratio_array[0] if undercharge_ratio_array is not None else None

        overcharge_pct = config.get("overcharge_percentage")
        overcharge_ratio_array = np.array(overcharge_pct) / 100.0 if overcharge_pct else None

        initial_soc_ratio = initial_soc / 100.0

        # Calculate early charge/discharge incentives (use first period if present)
        early_charge_list = config.get("early_charge_incentive")
        early_charge_incentive = early_charge_list[0] if early_charge_list else DEFAULTS[CONF_EARLY_CHARGE_INCENTIVE]

        # Determine unusable ratio for initial charge calculation
        unusable_ratio_first = undercharge_ratio_first if undercharge_ratio_first is not None else min_ratio_first

        # Calculate initial charge in kWh (remove unusable percentage)
        initial_charge = max((initial_soc_ratio - unusable_ratio_first) * capacity_first, 0.0)

        # Create battery sections and track their capacities
        section_names: list[str] = []
        section_capacities: dict[str, list[float]] = {}

        # 1. Undercharge section (if configured)
        if undercharge_ratio_array is not None and config.get("undercharge_cost") is not None:
            section_name = f"{name}:undercharge"
            section_names.append(section_name)
            # Time-varying capacity: (min_ratio - undercharge_ratio) * capacity per period
            undercharge_capacity = (min_ratio_array - undercharge_ratio_array) * capacity_array
            section_capacities[section_name] = undercharge_capacity.tolist()
            # For initial charge distribution, use first period capacity
            undercharge_capacity_first = float(undercharge_capacity[0])
            section_initial_charge = min(initial_charge, undercharge_capacity_first)

            elements.append(
                {
                    "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                    "name": section_name,
                    "capacity": undercharge_capacity.tolist(),
                    "initial_charge": section_initial_charge,
                }
            )

            initial_charge = max(initial_charge - section_initial_charge, 0.0)

        # 2. Normal section (always present)
        section_name = f"{name}:normal"
        section_names.append(section_name)
        # Time-varying capacity: (max_ratio - min_ratio) * capacity per period
        normal_capacity = (max_ratio_array - min_ratio_array) * capacity_array
        section_capacities[section_name] = normal_capacity.tolist()
        normal_capacity_first = float(normal_capacity[0])
        section_initial_charge = min(initial_charge, normal_capacity_first)

        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": section_name,
                "capacity": normal_capacity.tolist(),
                "initial_charge": section_initial_charge,
            }
        )

        initial_charge = max(initial_charge - section_initial_charge, 0.0)

        # 3. Overcharge section (if configured)
        if overcharge_ratio_array is not None and config.get("overcharge_cost") is not None:
            section_name = f"{name}:overcharge"
            section_names.append(section_name)
            # Time-varying capacity: (overcharge_ratio - max_ratio) * capacity per period
            overcharge_capacity = (overcharge_ratio_array - max_ratio_array) * capacity_array
            section_capacities[section_name] = overcharge_capacity.tolist()
            overcharge_capacity_first = float(overcharge_capacity[0])
            section_initial_charge = min(initial_charge, overcharge_capacity_first)

            elements.append(
                {
                    "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                    "name": section_name,
                    "capacity": overcharge_capacity.tolist(),
                    "initial_charge": section_initial_charge,
                }
            )

        # 4. Create internal node
        node_name = f"{name}:node"
        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": node_name,
                "is_source": False,
                "is_sink": False,
            }
        )

        # 5. Create connections from sections to internal node

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
                segments: list[SegmentSpec] = [
                    {
                        "segment_type": "pricing",
                        "price_target_source": np.array(charge_price),  # Overcharge penalty when charging
                    }
                ]
                elements.append(
                    {
                        "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                        "name": f"{section_name}:to_node",
                        "source": section_name,
                        "target": node_name,
                        "segments": segments,
                    }
                )
                continue
            else:
                discharge_price = None

            segments: list[SegmentSpec] = []
            if discharge_price is not None:
                segments.append(
                    {
                        "segment_type": "pricing",
                        "price_source_target": np.array(discharge_price),  # Undercharge penalty when discharging
                    }
                )
            section_connection: ModelElementConfig = {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{section_name}:to_node",
                "source": section_name,
                "target": node_name,
            }
            if segments:
                section_connection["segments"] = segments
            elements.append(section_connection)

        # 6. Create balance connections between adjacent sections (enforces fill ordering)
        # Balance connections ensure lower sections fill before upper sections
        # The BatteryBalanceConnection derives capacity from connected battery sections directly
        for i in range(len(section_names) - 1):
            lower_section = section_names[i]
            upper_section = section_names[i + 1]

            elements.append(
                {
                    "element_type": MODEL_ELEMENT_TYPE_BATTERY_BALANCE_CONNECTION,
                    "name": f"{name}:balance:{lower_section.split(':')[-1]}:{upper_section.split(':')[-1]}",
                    "upper": upper_section,
                    "lower": lower_section,
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

        discharge_costs = (
            [d + dc for d, dc in zip(discharge_early_incentive, config["discharge_cost"], strict=True)]
            if "discharge_cost" in config
            else discharge_early_incentive
        )
        segments: list[SegmentSpec] = []
        efficiency_values = config["efficiency"]
        efficiency_spec: EfficiencySegmentSpec = {
            "segment_type": "efficiency",
            "efficiency_source_target": np.array(efficiency_values) / 100.0,  # Node to network (discharge)
            "efficiency_target_source": np.array(efficiency_values) / 100.0,  # Network to node (charge)
        }
        segments.append(efficiency_spec)

        max_discharge = config.get("max_discharge_power")
        max_charge = config.get("max_charge_power")
        if max_discharge is not None or max_charge is not None:
            power_limit_spec: PowerLimitSegmentSpec = {"segment_type": "power_limit"}
            if max_discharge is not None:
                power_limit_spec["max_power_source_target"] = np.array(max_discharge)
            if max_charge is not None:
                power_limit_spec["max_power_target_source"] = np.array(max_charge)
            segments.append(power_limit_spec)

        pricing_spec: PricingSegmentSpec = {
            "segment_type": "pricing",
            "price_source_target": np.array(discharge_costs),
            "price_target_source": np.array(charge_early_incentive),
        }
        segments.append(pricing_spec)

        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:connection",
                "source": node_name,
                "target": config["connection"],
                "segments": segments,
            }
        )

        return elements

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        config: BatteryConfigData,
        **_kwargs: Any,
    ) -> Mapping[BatteryDeviceName, Mapping[BatteryOutputName, OutputData]]:
        """Map model outputs to battery-specific output names.

        Aggregates outputs from multiple battery sections and connections.
        Returns multiple devices for SOC regions based on what's configured.
        """
        # Collect section outputs
        section_outputs: dict[str, dict[ModelOutputName, OutputData]] = {}
        section_names: list[str] = []

        # Check for undercharge section
        undercharge_name = f"{name}:undercharge"
        if undercharge_name in model_outputs:
            section_outputs["undercharge"] = require_output_map(model_outputs[undercharge_name])
            section_names.append("undercharge")

        # Normal section (always present)
        normal_name = f"{name}:normal"
        if normal_name in model_outputs:
            section_outputs["normal"] = require_output_map(model_outputs[normal_name])
            section_names.append("normal")

        # Check for overcharge section
        overcharge_name = f"{name}:overcharge"
        if overcharge_name in model_outputs:
            section_outputs["overcharge"] = require_output_map(model_outputs[overcharge_name])
            section_names.append("overcharge")

        # Get node outputs for power balance
        node_name = f"{name}:node"
        node_outputs: dict[ModelOutputName, OutputData] = (
            require_output_map(model_outputs[node_name]) if node_name in model_outputs else {}
        )

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
            type=OutputType.POWER,
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

            section_device_outputs: dict[BatteryOutputName, OutputData] = {
                BATTERY_ENERGY_STORED: replace(section_data[model_battery.BATTERY_ENERGY_STORED], advanced=True),
                BATTERY_POWER_CHARGE: replace(section_data[model_battery.BATTERY_POWER_CHARGE], advanced=True),
                BATTERY_POWER_DISCHARGE: replace(section_data[model_battery.BATTERY_POWER_DISCHARGE], advanced=True),
                BATTERY_ENERGY_IN_FLOW: replace(section_data[model_battery.BATTERY_ENERGY_IN_FLOW], advanced=True),
                BATTERY_ENERGY_OUT_FLOW: replace(section_data[model_battery.BATTERY_ENERGY_OUT_FLOW], advanced=True),
                BATTERY_SOC_MAX: replace(section_data[model_battery.BATTERY_SOC_MAX], advanced=True),
                BATTERY_SOC_MIN: replace(section_data[model_battery.BATTERY_SOC_MIN], advanced=True),
            }

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
                    balance_data = require_output_map(model_outputs[balance_name])
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
                    balance_data = require_output_map(model_outputs[balance_name])
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
                    type=OutputType.POWER_FLOW,
                    unit="kW",
                    values=tuple(float(v) for v in power_down_values),
                    advanced=True,
                )
            if power_up_values is not None:
                result[device_key][BATTERY_BALANCE_POWER_UP] = OutputData(
                    type=OutputType.POWER_FLOW,
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
    # Capacity and percentage fields are already boundaries (n+1 values)
    capacity = np.array(config["capacity"])

    # Get time-varying min ratio (also boundaries)
    min_ratio = np.array(config["min_charge_percentage"]) / 100.0

    undercharge_pct = config.get("undercharge_percentage")
    undercharge_ratio = np.array(undercharge_pct) / 100.0 if undercharge_pct else None
    unusable_ratio = undercharge_ratio if undercharge_ratio is not None else min_ratio

    # Both energy values and capacity/ratios are now boundaries (n+1 values)
    inaccessible_energy = unusable_ratio * capacity
    total_values = np.array(aggregate_energy.values) + inaccessible_energy

    return OutputData(
        type=aggregate_energy.type,
        unit=aggregate_energy.unit,
        values=tuple(total_values.tolist()),
    )


def _calculate_soc(total_energy: OutputData, config: BatteryConfigData) -> OutputData:
    """Calculate SOC percentage from aggregate energy and total capacity."""
    # Capacity is already boundaries (n+1 values), same as energy
    capacity = np.array(config["capacity"])
    soc_values = np.array(total_energy.values) / capacity * 100.0

    return OutputData(
        type=OutputType.STATE_OF_CHARGE,
        unit="%",
        values=tuple(soc_values.tolist()),
    )
