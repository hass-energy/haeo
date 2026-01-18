"""Battery element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
import numpy as np

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.elements.input_fields import InputFieldDefaults, InputFieldInfo
from custom_components.haeo.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.model import battery as model_battery
from custom_components.haeo.model import battery_balance_connection as model_balance
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_BATTERY_BALANCE_CONNECTION,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
)
from custom_components.haeo.model.elements.node import NODE_POWER_BALANCE
from custom_components.haeo.model.output_data import OutputData

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

    def inputs(self, config: Any) -> dict[str, InputFieldInfo[Any]]:
        """Return input field definitions for battery elements."""
        _ = config
        return {
            CONF_CAPACITY: InputFieldInfo(
                field_name=CONF_CAPACITY,
                entity_description=NumberEntityDescription(
                    key=CONF_CAPACITY,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_CAPACITY}",
                    native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                    device_class=NumberDeviceClass.ENERGY_STORAGE,
                    native_min_value=0.1,
                    native_max_value=1000.0,
                    native_step=0.1,
                ),
                output_type=OutputType.ENERGY,
                time_series=True,
                boundaries=True,
            ),
            CONF_INITIAL_CHARGE_PERCENTAGE: InputFieldInfo(
                field_name=CONF_INITIAL_CHARGE_PERCENTAGE,
                entity_description=NumberEntityDescription(
                    key=CONF_INITIAL_CHARGE_PERCENTAGE,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_INITIAL_CHARGE_PERCENTAGE}",
                    native_unit_of_measurement=PERCENTAGE,
                    device_class=NumberDeviceClass.BATTERY,
                    native_min_value=0.0,
                    native_max_value=100.0,
                    native_step=0.1,
                ),
                output_type=OutputType.STATE_OF_CHARGE,
                time_series=True,
            ),
            CONF_MAX_CHARGE_POWER: InputFieldInfo(
                field_name=CONF_MAX_CHARGE_POWER,
                entity_description=NumberEntityDescription(
                    key=CONF_MAX_CHARGE_POWER,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_MAX_CHARGE_POWER}",
                    native_unit_of_measurement=UnitOfPower.KILO_WATT,
                    device_class=NumberDeviceClass.POWER,
                    native_min_value=0.0,
                    native_max_value=1000.0,
                    native_step=0.1,
                ),
                output_type=OutputType.POWER,
                direction="+",
                time_series=True,
                defaults=InputFieldDefaults(mode="entity"),
            ),
            CONF_MAX_DISCHARGE_POWER: InputFieldInfo(
                field_name=CONF_MAX_DISCHARGE_POWER,
                entity_description=NumberEntityDescription(
                    key=CONF_MAX_DISCHARGE_POWER,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_MAX_DISCHARGE_POWER}",
                    native_unit_of_measurement=UnitOfPower.KILO_WATT,
                    device_class=NumberDeviceClass.POWER,
                    native_min_value=0.0,
                    native_max_value=1000.0,
                    native_step=0.1,
                ),
                output_type=OutputType.POWER,
                direction="-",
                time_series=True,
                defaults=InputFieldDefaults(mode="entity"),
            ),
            CONF_EFFICIENCY: InputFieldInfo(
                field_name=CONF_EFFICIENCY,
                entity_description=NumberEntityDescription(
                    key=CONF_EFFICIENCY,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_EFFICIENCY}",
                    native_unit_of_measurement=PERCENTAGE,
                    device_class=NumberDeviceClass.POWER_FACTOR,
                    native_min_value=50.0,
                    native_max_value=100.0,
                    native_step=0.1,
                ),
                output_type=OutputType.EFFICIENCY,
                time_series=True,
                defaults=InputFieldDefaults(mode="value", value=95.0),
            ),
            CONF_EARLY_CHARGE_INCENTIVE: InputFieldInfo(
                field_name=CONF_EARLY_CHARGE_INCENTIVE,
                entity_description=NumberEntityDescription(
                    key=CONF_EARLY_CHARGE_INCENTIVE,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_EARLY_CHARGE_INCENTIVE}",
                    native_min_value=0.0,
                    native_max_value=1.0,
                    native_step=0.001,
                ),
                output_type=OutputType.PRICE,
                direction="-",
                time_series=True,
                defaults=InputFieldDefaults(mode="value", value=0.001),
            ),
            CONF_MIN_CHARGE_PERCENTAGE: InputFieldInfo(
                field_name=CONF_MIN_CHARGE_PERCENTAGE,
                entity_description=NumberEntityDescription(
                    key=CONF_MIN_CHARGE_PERCENTAGE,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_MIN_CHARGE_PERCENTAGE}",
                    native_unit_of_measurement=PERCENTAGE,
                    device_class=NumberDeviceClass.BATTERY,
                    native_min_value=0.0,
                    native_max_value=100.0,
                    native_step=1.0,
                ),
                output_type=OutputType.STATE_OF_CHARGE,
                time_series=True,
                boundaries=True,
                defaults=InputFieldDefaults(mode=None, value=0.0),
            ),
            CONF_MAX_CHARGE_PERCENTAGE: InputFieldInfo(
                field_name=CONF_MAX_CHARGE_PERCENTAGE,
                entity_description=NumberEntityDescription(
                    key=CONF_MAX_CHARGE_PERCENTAGE,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_MAX_CHARGE_PERCENTAGE}",
                    native_unit_of_measurement=PERCENTAGE,
                    device_class=NumberDeviceClass.BATTERY,
                    native_min_value=0.0,
                    native_max_value=100.0,
                    native_step=1.0,
                ),
                output_type=OutputType.STATE_OF_CHARGE,
                time_series=True,
                boundaries=True,
                defaults=InputFieldDefaults(mode=None, value=100.0),
            ),
            CONF_DISCHARGE_COST: InputFieldInfo(
                field_name=CONF_DISCHARGE_COST,
                entity_description=NumberEntityDescription(
                    key=CONF_DISCHARGE_COST,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_DISCHARGE_COST}",
                    native_min_value=0.0,
                    native_max_value=1.0,
                    native_step=0.001,
                ),
                output_type=OutputType.PRICE,
                direction="-",
                time_series=True,
            ),
            CONF_UNDERCHARGE_PERCENTAGE: InputFieldInfo(
                field_name=CONF_UNDERCHARGE_PERCENTAGE,
                entity_description=NumberEntityDescription(
                    key=CONF_UNDERCHARGE_PERCENTAGE,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_UNDERCHARGE_PERCENTAGE}",
                    native_unit_of_measurement=PERCENTAGE,
                    device_class=NumberDeviceClass.BATTERY,
                    native_min_value=0.0,
                    native_max_value=100.0,
                    native_step=1.0,
                ),
                output_type=OutputType.STATE_OF_CHARGE,
                time_series=True,
                boundaries=True,
                defaults=InputFieldDefaults(mode="value", value=0),
                device_type=BATTERY_DEVICE_UNDERCHARGE,
            ),
            CONF_UNDERCHARGE_COST: InputFieldInfo(
                field_name=CONF_UNDERCHARGE_COST,
                entity_description=NumberEntityDescription(
                    key=CONF_UNDERCHARGE_COST,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_UNDERCHARGE_COST}",
                    native_min_value=0.0,
                    native_max_value=10.0,
                    native_step=0.001,
                ),
                output_type=OutputType.PRICE,
                direction="-",
                time_series=True,
                defaults=InputFieldDefaults(mode="value", value=0),
                device_type=BATTERY_DEVICE_UNDERCHARGE,
            ),
            CONF_OVERCHARGE_PERCENTAGE: InputFieldInfo(
                field_name=CONF_OVERCHARGE_PERCENTAGE,
                entity_description=NumberEntityDescription(
                    key=CONF_OVERCHARGE_PERCENTAGE,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_OVERCHARGE_PERCENTAGE}",
                    native_unit_of_measurement=PERCENTAGE,
                    device_class=NumberDeviceClass.BATTERY,
                    native_min_value=0.0,
                    native_max_value=100.0,
                    native_step=1.0,
                ),
                output_type=OutputType.STATE_OF_CHARGE,
                time_series=True,
                boundaries=True,
                defaults=InputFieldDefaults(mode="value", value=100),
                device_type=BATTERY_DEVICE_OVERCHARGE,
            ),
            CONF_OVERCHARGE_COST: InputFieldInfo(
                field_name=CONF_OVERCHARGE_COST,
                entity_description=NumberEntityDescription(
                    key=CONF_OVERCHARGE_COST,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_OVERCHARGE_COST}",
                    native_min_value=0.0,
                    native_max_value=10.0,
                    native_step=0.001,
                ),
                output_type=OutputType.PRICE,
                direction="-",
                time_series=True,
                defaults=InputFieldDefaults(mode="value", value=0),
                device_type=BATTERY_DEVICE_OVERCHARGE,
            ),
        }

    def build_config_data(
        self,
        loaded_values: Mapping[str, Any],
        config: BatteryConfigSchema,
    ) -> BatteryConfigData:
        """Build ConfigData from pre-loaded values.

        This is the single source of truth for ConfigData construction.
        The coordinator uses this method after loading input entity values.

        Args:
            loaded_values: Dict of field names to loaded values (from input entities)
            config: Original ConfigSchema for non-input fields (element_type, name, connection)

        Returns:
            BatteryConfigData with all fields populated and defaults applied

        """
        # Determine array sizes from capacity (a required boundary field)
        capacity = np.asarray(loaded_values["capacity"], dtype=float)
        n_boundaries = len(capacity)
        n_periods = max(0, n_boundaries - 1)

        # Apply defaults for optional fields with defaults
        min_charge = np.asarray(
            loaded_values.get(
                CONF_MIN_CHARGE_PERCENTAGE,
                np.full(n_boundaries, DEFAULTS[CONF_MIN_CHARGE_PERCENTAGE], dtype=float),
            ),
            dtype=float,
        )
        max_charge = np.asarray(
            loaded_values.get(
                CONF_MAX_CHARGE_PERCENTAGE,
                np.full(n_boundaries, DEFAULTS[CONF_MAX_CHARGE_PERCENTAGE], dtype=float),
            ),
            dtype=float,
        )
        efficiency = np.asarray(
            loaded_values.get(
                CONF_EFFICIENCY,
                np.full(n_periods, DEFAULTS[CONF_EFFICIENCY], dtype=float),
            ),
            dtype=float,
        )

        # Build data with required fields and defaults
        data: BatteryConfigData = {
            "element_type": config["element_type"],
            "name": config["name"],
            "connection": config[CONF_CONNECTION],
            "capacity": capacity,
            "initial_charge_percentage": np.asarray(loaded_values["initial_charge_percentage"], dtype=float),
            "min_charge_percentage": min_charge,
            "max_charge_percentage": max_charge,
            "efficiency": efficiency,
        }

        # Optional fields without defaults - only include if present in loaded_values
        if CONF_MAX_CHARGE_POWER in loaded_values:
            data["max_charge_power"] = np.asarray(loaded_values[CONF_MAX_CHARGE_POWER], dtype=float)

        if CONF_MAX_DISCHARGE_POWER in loaded_values:
            data["max_discharge_power"] = np.asarray(loaded_values[CONF_MAX_DISCHARGE_POWER], dtype=float)

        if CONF_DISCHARGE_COST in loaded_values:
            data["discharge_cost"] = np.asarray(loaded_values[CONF_DISCHARGE_COST], dtype=float)

        if CONF_EARLY_CHARGE_INCENTIVE in loaded_values:
            data["early_charge_incentive"] = np.asarray(loaded_values[CONF_EARLY_CHARGE_INCENTIVE], dtype=float)

        if CONF_UNDERCHARGE_PERCENTAGE in loaded_values:
            data["undercharge_percentage"] = np.asarray(loaded_values[CONF_UNDERCHARGE_PERCENTAGE], dtype=float)

        if CONF_OVERCHARGE_PERCENTAGE in loaded_values:
            data["overcharge_percentage"] = np.asarray(loaded_values[CONF_OVERCHARGE_PERCENTAGE], dtype=float)

        if CONF_UNDERCHARGE_COST in loaded_values:
            data["undercharge_cost"] = np.asarray(loaded_values[CONF_UNDERCHARGE_COST], dtype=float)

        if CONF_OVERCHARGE_COST in loaded_values:
            data["overcharge_cost"] = np.asarray(loaded_values[CONF_OVERCHARGE_COST], dtype=float)

        return data

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
        capacity_array = config["capacity"]
        capacity_first = capacity_array[0]
        initial_soc = config["initial_charge_percentage"][0]

        # Convert percentages to ratio arrays for time-varying limits
        min_ratio_array = config["min_charge_percentage"] / 100.0
        max_ratio_array = config["max_charge_percentage"] / 100.0
        min_ratio_first = min_ratio_array[0]

        # Get optional percentage arrays (if present)
        undercharge_pct = config.get("undercharge_percentage")
        undercharge_ratio_array = undercharge_pct / 100.0 if undercharge_pct is not None else None
        undercharge_ratio_first = undercharge_ratio_array[0] if undercharge_ratio_array is not None else None

        overcharge_pct = config.get("overcharge_percentage")
        overcharge_ratio_array = overcharge_pct / 100.0 if overcharge_pct is not None else None

        initial_soc_ratio = initial_soc / 100.0

        # Calculate early charge/discharge incentives (use first period if present)
        early_charge_list = config.get("early_charge_incentive")
        early_charge_incentive = (
            float(early_charge_list[0]) if early_charge_list is not None else DEFAULTS[CONF_EARLY_CHARGE_INCENTIVE]
        )

        # Determine unusable ratio for initial charge calculation
        unusable_ratio_first = undercharge_ratio_first if undercharge_ratio_first is not None else min_ratio_first

        # Calculate initial charge in kWh (remove unusable percentage)
        initial_charge = max((initial_soc_ratio - unusable_ratio_first) * capacity_first, 0.0)

        # Create battery sections and track their capacities
        section_names: list[str] = []
        section_capacities: dict[str, np.ndarray] = {}

        # 1. Undercharge section (if configured)
        if undercharge_ratio_array is not None and config.get("undercharge_cost") is not None:
            section_name = f"{name}:undercharge"
            section_names.append(section_name)
            # Time-varying capacity: (min_ratio - undercharge_ratio) * capacity per period
            undercharge_capacity = (min_ratio_array - undercharge_ratio_array) * capacity_array
            section_capacities[section_name] = undercharge_capacity
            # For initial charge distribution, use first period capacity
            undercharge_capacity_first = float(undercharge_capacity[0])
            section_initial_charge = min(initial_charge, undercharge_capacity_first)

            elements.append(
                {
                    "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                    "name": section_name,
                    "capacity": undercharge_capacity,
                    "initial_charge": section_initial_charge,
                }
            )

            initial_charge = max(initial_charge - section_initial_charge, 0.0)

        # 2. Normal section (always present)
        section_name = f"{name}:normal"
        section_names.append(section_name)
        # Time-varying capacity: (max_ratio - min_ratio) * capacity per period
        normal_capacity = (max_ratio_array - min_ratio_array) * capacity_array
        section_capacities[section_name] = normal_capacity
        normal_capacity_first = float(normal_capacity[0])
        section_initial_charge = min(initial_charge, normal_capacity_first)

        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": section_name,
                "capacity": normal_capacity,
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
            section_capacities[section_name] = overcharge_capacity
            overcharge_capacity_first = float(overcharge_capacity[0])
            section_initial_charge = min(initial_charge, overcharge_capacity_first)

            elements.append(
                {
                    "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                    "name": section_name,
                    "capacity": overcharge_capacity,
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
        undercharge_cost_array = (
            config["undercharge_cost"] if "undercharge_cost" in config else np.zeros(n_periods, dtype=float)
        )
        overcharge_cost_array = (
            config["overcharge_cost"] if "overcharge_cost" in config else np.zeros(n_periods, dtype=float)
        )

        for section_name in section_names:
            # Determine discharge costs based on section (undercharge/overcharge penalties)
            # Ordering is enforced by balance connections, not price incentives
            if "undercharge" in section_name:
                discharge_price = undercharge_cost_array
            elif "overcharge" in section_name:
                charge_price = overcharge_cost_array
                elements.append(
                    {
                        "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                        "name": f"{section_name}:to_node",
                        "source": section_name,
                        "target": node_name,
                        "segments": {
                            "pricing": {
                                "segment_type": "pricing",
                                "price_source_target": None,
                                "price_target_source": charge_price,  # Overcharge penalty when charging
                            }
                        },
                    }
                )
                continue
            else:
                discharge_price = None

            elements.append(
                {
                    "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                    "name": f"{section_name}:to_node",
                    "source": section_name,
                    "target": node_name,
                    "segments": {
                        "pricing": {
                            "segment_type": "pricing",
                            "price_source_target": discharge_price,  # Undercharge penalty when discharging
                            "price_target_source": None,
                        }
                    },
                }
            )

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
        ramp = np.arange(n_periods, dtype=float) / max(n_periods - 1, 1) if n_periods else np.array([], dtype=float)
        charge_early_incentive = -early_charge_incentive + (early_charge_incentive * ramp)
        discharge_early_incentive = early_charge_incentive + (early_charge_incentive * ramp)

        discharge_costs = (
            discharge_early_incentive + config["discharge_cost"]
            if "discharge_cost" in config
            else discharge_early_incentive
        )
        efficiency_values = config["efficiency"]
        max_discharge = config.get("max_discharge_power")
        max_charge = config.get("max_charge_power")

        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:connection",
                "source": node_name,
                "target": config["connection"],
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency_source_target": efficiency_values / 100.0,  # Node to network (discharge)
                        "efficiency_target_source": efficiency_values / 100.0,  # Network to node (charge)
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": max_discharge,
                        "max_power_target_source": max_charge,
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price_source_target": discharge_costs,
                        "price_target_source": charge_early_incentive,
                    },
                },
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
            undercharge_outputs: dict[ModelOutputName, OutputData] = {}
            for key, value in model_outputs[undercharge_name].items():
                if not isinstance(value, OutputData):
                    msg = f"Expected OutputData for {undercharge_name!r} output {key!r}"
                    raise TypeError(msg)
                undercharge_outputs[key] = value
            section_outputs["undercharge"] = undercharge_outputs
            section_names.append("undercharge")

        # Normal section (always present)
        normal_name = f"{name}:normal"
        if normal_name in model_outputs:
            normal_outputs: dict[ModelOutputName, OutputData] = {}
            for key, value in model_outputs[normal_name].items():
                if not isinstance(value, OutputData):
                    msg = f"Expected OutputData for {normal_name!r} output {key!r}"
                    raise TypeError(msg)
                normal_outputs[key] = value
            section_outputs["normal"] = normal_outputs
            section_names.append("normal")

        # Check for overcharge section
        overcharge_name = f"{name}:overcharge"
        if overcharge_name in model_outputs:
            overcharge_outputs: dict[ModelOutputName, OutputData] = {}
            for key, value in model_outputs[overcharge_name].items():
                if not isinstance(value, OutputData):
                    msg = f"Expected OutputData for {overcharge_name!r} output {key!r}"
                    raise TypeError(msg)
                overcharge_outputs[key] = value
            section_outputs["overcharge"] = overcharge_outputs
            section_names.append("overcharge")

        # Get node outputs for power balance
        node_name = f"{name}:node"
        node_outputs: dict[ModelOutputName, OutputData] = {}
        if node_name in model_outputs:
            for key, value in model_outputs[node_name].items():
                if not isinstance(value, OutputData):
                    msg = f"Expected OutputData for {node_name!r} output {key!r}"
                    raise TypeError(msg)
                node_outputs[key] = value

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
                    # Power down from this section to lower section (energy leaving downward)
                    balance_outputs = model_outputs[balance_name]
                    down_output = balance_outputs.get(model_balance.BALANCE_POWER_DOWN)
                    if isinstance(down_output, OutputData):
                        down_vals = down_output.values
                        power_down_values = list(down_vals)
                    # Power up from lower section to this section (energy entering from below)
                    up_output = balance_outputs.get(model_balance.BALANCE_POWER_UP)
                    if isinstance(up_output, OutputData):
                        up_vals = up_output.values
                        power_up_values = list(up_vals)

            # Check for balance connection with section above (this section is lower)
            # In this connection: power_down enters this section, power_up leaves this section
            if i < len(section_names) - 1:
                upper_key = section_names[i + 1]
                balance_name = f"{name}:balance:{section_key}:{upper_key}"
                if balance_name in model_outputs:
                    # Power down from upper section to this section (energy entering from above)
                    balance_outputs = model_outputs[balance_name]
                    down_output = balance_outputs.get(model_balance.BALANCE_POWER_DOWN)
                    if isinstance(down_output, OutputData):
                        down_vals = np.array(down_output.values)
                        if power_down_values is None:
                            power_down_values = list(down_vals)
                        else:
                            power_down_values = list(np.array(power_down_values) + down_vals)
                    # Power up from this section to upper section (energy leaving upward)
                    up_output = balance_outputs.get(model_balance.BALANCE_POWER_UP)
                    if isinstance(up_output, OutputData):
                        up_vals = np.array(up_output.values)
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
    capacity = config["capacity"]

    # Get time-varying min ratio (also boundaries)
    min_ratio = config["min_charge_percentage"] / 100.0

    undercharge_pct = config.get("undercharge_percentage")
    undercharge_ratio = undercharge_pct / 100.0 if undercharge_pct is not None else None
    unusable_ratio = undercharge_ratio if undercharge_ratio is not None else min_ratio

    # Both energy values and capacity/ratios are now boundaries (n+1 values)
    inaccessible_energy = unusable_ratio * capacity
    total_values = np.asarray(aggregate_energy.values, dtype=float) + inaccessible_energy

    return OutputData(
        type=aggregate_energy.type,
        unit=aggregate_energy.unit,
        values=tuple(total_values.tolist()),
    )


def _calculate_soc(total_energy: OutputData, config: BatteryConfigData) -> OutputData:
    """Calculate SOC percentage from aggregate energy and total capacity."""
    # Capacity is already boundaries (n+1 values), same as energy
    capacity = config["capacity"]
    soc_values = np.asarray(total_energy.values, dtype=float) / capacity * 100.0

    return OutputData(
        type=OutputType.STATE_OF_CHARGE,
        unit="%",
        values=tuple(soc_values.tolist()),
    )
