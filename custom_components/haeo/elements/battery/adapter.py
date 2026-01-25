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
from custom_components.haeo.elements.output_utils import expect_output_data
from custom_components.haeo.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.model import battery as model_battery
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_BATTERY, MODEL_ELEMENT_TYPE_CONNECTION
from custom_components.haeo.model.elements.segments import SegmentSpec, SocPricingSegmentSpec
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.util import broadcast_to_sequence

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
    CONF_SECTION_ADVANCED,
    CONF_SECTION_BASIC,
    CONF_SECTION_LIMITS,
    CONF_SECTION_OVERCHARGE,
    CONF_SECTION_UNDERCHARGE,
    CONF_UNDERCHARGE_COST,
    CONF_UNDERCHARGE_PERCENTAGE,
    ELEMENT_TYPE,
    BatteryConfigData,
    BatteryConfigSchema,
)

# Default ratio values for optional fields applied by adapter
DEFAULTS: Final[dict[str, float]] = {
    CONF_MIN_CHARGE_PERCENTAGE: 0.0,
    CONF_MAX_CHARGE_PERCENTAGE: 1.0,
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
    )
)

type BatteryDeviceName = Literal["battery"]

BATTERY_DEVICE_NAMES: Final[frozenset[BatteryDeviceName]] = frozenset((BATTERY_DEVICE_BATTERY := "battery",))


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

        basic = config[CONF_SECTION_BASIC]
        limits = config[CONF_SECTION_LIMITS]
        advanced = config[CONF_SECTION_ADVANCED]
        undercharge = config.get(CONF_SECTION_UNDERCHARGE, {})
        overcharge = config.get(CONF_SECTION_OVERCHARGE, {})

        # Check required fields
        if not entity_available(basic.get(CONF_CAPACITY)):
            return False
        if not entity_available(basic.get(CONF_INITIAL_CHARGE_PERCENTAGE)):
            return False

        # Check optional time series fields if present
        optional_checks = [
            (limits, CONF_MAX_CHARGE_POWER),
            (limits, CONF_MAX_DISCHARGE_POWER),
            (limits, CONF_MIN_CHARGE_PERCENTAGE),
            (limits, CONF_MAX_CHARGE_PERCENTAGE),
            (advanced, CONF_EFFICIENCY),
            (advanced, CONF_EARLY_CHARGE_INCENTIVE),
            (advanced, CONF_DISCHARGE_COST),
            (undercharge, CONF_UNDERCHARGE_PERCENTAGE),
            (undercharge, CONF_UNDERCHARGE_COST),
            (overcharge, CONF_OVERCHARGE_PERCENTAGE),
            (overcharge, CONF_OVERCHARGE_COST),
        ]
        return all(entity_available(section.get(field)) for section, field in optional_checks)

    def inputs(self, config: Any) -> dict[str, dict[str, InputFieldInfo[Any]]]:
        """Return input field definitions for battery elements."""
        _ = config
        return {
            CONF_SECTION_BASIC: {
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
            },
            CONF_SECTION_LIMITS: {
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
            },
            CONF_SECTION_ADVANCED: {
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
            },
            CONF_SECTION_UNDERCHARGE: _partition_input_fields(
                percentage_key=CONF_UNDERCHARGE_PERCENTAGE,
                cost_key=CONF_UNDERCHARGE_COST,
                percentage_default=0,
                cost_default=0,
                cost_direction="-",
            ),
            CONF_SECTION_OVERCHARGE: _partition_input_fields(
                percentage_key=CONF_OVERCHARGE_PERCENTAGE,
                cost_key=CONF_OVERCHARGE_COST,
                percentage_default=100,
                cost_default=0,
                cost_direction="-",
            ),
        }

    def model_elements(self, config: BatteryConfigData) -> list[ModelElementConfig]:
        """Create model elements for Battery configuration.

        Creates a single battery element and a connection to the target.
        """
        basic = config[CONF_SECTION_BASIC]
        limits = config[CONF_SECTION_LIMITS]
        advanced = config[CONF_SECTION_ADVANCED]
        undercharge = config.get(CONF_SECTION_UNDERCHARGE, {})
        overcharge = config.get(CONF_SECTION_OVERCHARGE, {})

        name = basic["name"]
        elements: list[ModelElementConfig] = []
        # capacity is boundaries (n+1 values), so n_periods = len - 1
        n_boundaries = len(basic[CONF_CAPACITY])
        n_periods = n_boundaries - 1

        capacity = basic[CONF_CAPACITY]
        capacity_first = float(capacity[0])
        initial_soc = float(basic[CONF_INITIAL_CHARGE_PERCENTAGE][0])

        min_charge_percentage = limits.get(CONF_MIN_CHARGE_PERCENTAGE, DEFAULTS[CONF_MIN_CHARGE_PERCENTAGE])
        max_charge_percentage = limits.get(CONF_MAX_CHARGE_PERCENTAGE, DEFAULTS[CONF_MAX_CHARGE_PERCENTAGE])
        efficiency = advanced.get(CONF_EFFICIENCY)

        undercharge_cost = undercharge.get(CONF_UNDERCHARGE_COST)
        overcharge_cost = overcharge.get(CONF_OVERCHARGE_COST)
        undercharge_percentage = undercharge.get(CONF_UNDERCHARGE_PERCENTAGE) if undercharge_cost is not None else None
        overcharge_percentage = overcharge.get(CONF_OVERCHARGE_PERCENTAGE) if overcharge_cost is not None else None

        lower_ratio = undercharge_percentage if undercharge_percentage is not None else min_charge_percentage
        upper_ratio = overcharge_percentage if overcharge_percentage is not None else max_charge_percentage

        lower_ratio_first = float(lower_ratio[0]) if isinstance(lower_ratio, np.ndarray) else float(lower_ratio)

        capacity_range = (upper_ratio - lower_ratio) * capacity
        capacity_range_first = float(capacity_range[0])

        initial_charge = max(min((initial_soc - lower_ratio_first) * capacity_first, capacity_range_first), 0.0)

        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": name,
                "capacity": capacity_range,
                "initial_charge": initial_charge,
            }
        )

        # Calculate early charge/discharge incentives (use first period if present)
        early_charge_list = advanced.get(CONF_EARLY_CHARGE_INCENTIVE)
        early_charge_incentive = (
            float(early_charge_list[0]) if early_charge_list is not None else DEFAULTS[CONF_EARLY_CHARGE_INCENTIVE]
        )

        # Create connection from battery to target
        # Time-varying early charge incentive applied here (charge earlier in horizon)
        ramp = np.arange(n_periods, dtype=float) / max(n_periods - 1, 1) if n_periods else np.array([], dtype=float)
        charge_early_incentive = -early_charge_incentive + (early_charge_incentive * ramp)
        discharge_early_incentive = early_charge_incentive + (early_charge_incentive * ramp)

        discharge_cost = advanced.get(CONF_DISCHARGE_COST)
        discharge_costs = (
            discharge_early_incentive + discharge_cost if discharge_cost is not None else discharge_early_incentive
        )
        max_discharge = limits.get(CONF_MAX_DISCHARGE_POWER)
        max_charge = limits.get(CONF_MAX_CHARGE_POWER)

        soc_pricing_spec: SocPricingSegmentSpec | None = None
        if undercharge_percentage is not None and undercharge_cost is not None:
            min_ratio_series = broadcast_to_sequence(min_charge_percentage, n_periods + 1)[1:]
            lower_ratio_series = broadcast_to_sequence(lower_ratio, n_periods + 1)[1:]
            discharge_energy_threshold = (min_ratio_series - lower_ratio_series) * capacity[1:]
            soc_pricing_spec = {
                "segment_type": "soc_pricing",
                "discharge_energy_threshold": discharge_energy_threshold,
                "discharge_energy_price": undercharge_cost,
            }

        if overcharge_percentage is not None and overcharge_cost is not None:
            max_ratio_series = broadcast_to_sequence(max_charge_percentage, n_periods + 1)[1:]
            lower_ratio_series = broadcast_to_sequence(lower_ratio, n_periods + 1)[1:]
            charge_capacity_threshold = (max_ratio_series - lower_ratio_series) * capacity[1:]
            if soc_pricing_spec is None:
                soc_pricing_spec = {
                    "segment_type": "soc_pricing",
                    "charge_capacity_threshold": charge_capacity_threshold,
                    "charge_capacity_price": overcharge_cost,
                }
            else:
                soc_pricing_spec = {
                    **soc_pricing_spec,
                    "charge_capacity_threshold": charge_capacity_threshold,
                    "charge_capacity_price": overcharge_cost,
                }

        segments: dict[str, SegmentSpec] = {
            "efficiency": {
                "segment_type": "efficiency",
                "efficiency_source_target": efficiency,  # Battery to network (discharge)
                "efficiency_target_source": efficiency,  # Network to battery (charge)
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
        }
        if soc_pricing_spec is not None:
            segments["soc_pricing"] = soc_pricing_spec

        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:connection",
                "source": name,
                "target": basic[CONF_CONNECTION],
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

        Maps outputs from a single battery model element.
        """
        battery_outputs = {key: expect_output_data(value) for key, value in model_outputs[name].items()}

        power_charge = battery_outputs[model_battery.BATTERY_POWER_CHARGE]
        power_discharge = battery_outputs[model_battery.BATTERY_POWER_DISCHARGE]
        energy_stored = battery_outputs[model_battery.BATTERY_ENERGY_STORED]

        total_energy_stored = _calculate_total_energy(energy_stored, config)
        aggregate_soc = _calculate_soc(total_energy_stored, config)

        aggregate_outputs: dict[BatteryOutputName, OutputData] = {
            BATTERY_POWER_CHARGE: power_charge,
            BATTERY_POWER_DISCHARGE: power_discharge,
            BATTERY_ENERGY_STORED: total_energy_stored,
            BATTERY_STATE_OF_CHARGE: aggregate_soc,
        }

        aggregate_outputs[BATTERY_POWER_ACTIVE] = replace(
            power_discharge,
            values=[d - c for d, c in zip(power_discharge.values, power_charge.values, strict=True)],
            direction=None,
            type=OutputType.POWER,
        )

        aggregate_outputs[BATTERY_POWER_BALANCE] = battery_outputs[model_battery.BATTERY_POWER_BALANCE]
        aggregate_outputs[BATTERY_ENERGY_IN_FLOW] = replace(
            battery_outputs[model_battery.BATTERY_ENERGY_IN_FLOW], advanced=True
        )
        aggregate_outputs[BATTERY_ENERGY_OUT_FLOW] = replace(
            battery_outputs[model_battery.BATTERY_ENERGY_OUT_FLOW], advanced=True
        )
        aggregate_outputs[BATTERY_SOC_MAX] = replace(battery_outputs[model_battery.BATTERY_SOC_MAX], advanced=True)
        aggregate_outputs[BATTERY_SOC_MIN] = replace(battery_outputs[model_battery.BATTERY_SOC_MIN], advanced=True)

        return {BATTERY_DEVICE_BATTERY: aggregate_outputs}


adapter = BatteryAdapter()


def _partition_input_fields(
    *,
    percentage_key: str,
    cost_key: str,
    percentage_default: int,
    cost_default: int,
    cost_direction: str,
) -> dict[str, InputFieldInfo[Any]]:
    """Build shared input field definitions for partition sections."""
    return {
        percentage_key: InputFieldInfo(
            field_name=percentage_key,
            entity_description=NumberEntityDescription(
                key=percentage_key,
                translation_key=f"{ELEMENT_TYPE}_{percentage_key}",
                native_unit_of_measurement=PERCENTAGE,
                device_class=NumberDeviceClass.BATTERY,
                native_min_value=0.0,
                native_max_value=100.0,
                native_step=1.0,
            ),
            output_type=OutputType.STATE_OF_CHARGE,
            time_series=True,
            boundaries=True,
            defaults=InputFieldDefaults(mode="value", value=percentage_default),
        ),
        cost_key: InputFieldInfo(
            field_name=cost_key,
            entity_description=NumberEntityDescription(
                key=cost_key,
                translation_key=f"{ELEMENT_TYPE}_{cost_key}",
                native_min_value=0.0,
                native_max_value=10.0,
                native_step=0.001,
            ),
            output_type=OutputType.PRICE,
            direction=cost_direction,
            time_series=True,
            defaults=InputFieldDefaults(mode="value", value=cost_default),
        ),
    }


def _calculate_total_energy(aggregate_energy: OutputData, config: BatteryConfigData) -> OutputData:
    """Calculate total energy stored including inaccessible energy below min SOC."""
    # Capacity and ratio fields are already boundaries (n+1 values)
    capacity = config[CONF_SECTION_BASIC][CONF_CAPACITY]

    # Get time-varying min ratio (also boundaries)
    min_charge_percentage = config[CONF_SECTION_LIMITS].get(
        CONF_MIN_CHARGE_PERCENTAGE,
        DEFAULTS[CONF_MIN_CHARGE_PERCENTAGE],
    )
    undercharge = config.get(CONF_SECTION_UNDERCHARGE, {})
    undercharge_cost = undercharge.get(CONF_UNDERCHARGE_COST)
    undercharge_pct = undercharge.get(CONF_UNDERCHARGE_PERCENTAGE) if undercharge_cost is not None else None
    unusable_ratio = undercharge_pct if undercharge_pct is not None else min_charge_percentage

    # Both energy values and capacity/ratios are now boundaries (n+1 values)
    inaccessible_energy = unusable_ratio * capacity
    total_values = np.asarray(aggregate_energy.values, dtype=float) + inaccessible_energy

    return OutputData(
        type=aggregate_energy.type,
        unit=aggregate_energy.unit,
        values=tuple(total_values.tolist()),
    )


def _calculate_soc(total_energy: OutputData, config: BatteryConfigData) -> OutputData:
    """Calculate SOC ratio from aggregate energy and total capacity."""
    # Capacity is already boundaries (n+1 values), same as energy
    capacity = config[CONF_SECTION_BASIC][CONF_CAPACITY]
    soc_values = np.asarray(total_energy.values, dtype=float) / capacity

    return OutputData(
        type=OutputType.STATE_OF_CHARGE,
        unit="%",
        values=tuple(soc_values.tolist()),
    )
