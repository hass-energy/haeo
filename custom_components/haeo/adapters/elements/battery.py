"""Battery element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.adapters.output_utils import expect_output_data
from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.core.units import UnitOfMeasurement
from custom_components.haeo.elements.input_fields import InputFieldDefaults, InputFieldInfo
from custom_components.haeo.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.model import battery as model_battery
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_BATTERY, MODEL_ELEMENT_TYPE_CONNECTION
from custom_components.haeo.model.elements.segments import SegmentSpec, SocPricingSegmentSpec
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.util import broadcast_to_sequence
from custom_components.haeo.schema import extract_connection_target
from custom_components.haeo.schema.elements import ElementType
from custom_components.haeo.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_PARTITION_COST,
    CONF_PARTITION_PERCENTAGE,
    CONF_SALVAGE_VALUE,
    ELEMENT_TYPE,
    SECTION_LIMITS,
    SECTION_OVERCHARGE,
    SECTION_STORAGE,
    SECTION_UNDERCHARGE,
    BatteryConfigData,
)
from custom_components.haeo.sections import (
    CONF_CONNECTION,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)

# Default ratio values for optional fields applied by adapter
DEFAULTS: Final[dict[str, float]] = {
    CONF_MIN_CHARGE_PERCENTAGE: 0.0,
    CONF_MAX_CHARGE_PERCENTAGE: 1.0,
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

type BatteryDeviceName = Literal[ElementType.BATTERY]

BATTERY_DEVICE_NAMES: Final[frozenset[BatteryDeviceName]] = frozenset((BATTERY_DEVICE_BATTERY := ElementType.BATTERY,))


class BatteryAdapter:
    """Adapter for Battery elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.ADVANCED

    def inputs(self, config: Any) -> dict[str, dict[str, InputFieldInfo[Any]]]:
        """Return input field definitions for battery elements."""
        _ = config
        return {
            SECTION_STORAGE: {
                CONF_CAPACITY: InputFieldInfo(
                    field_name=CONF_CAPACITY,
                    entity_description=NumberEntityDescription(
                        key=CONF_CAPACITY,
                        translation_key=f"{ELEMENT_TYPE}_{CONF_CAPACITY}",
                        native_unit_of_measurement=UnitOfMeasurement.KILO_WATT_HOUR,
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
                        native_unit_of_measurement=UnitOfMeasurement.PERCENT,
                        device_class=NumberDeviceClass.BATTERY,
                        native_min_value=0.0,
                        native_max_value=100.0,
                        native_step=0.1,
                    ),
                    output_type=OutputType.STATE_OF_CHARGE,
                    time_series=False,
                ),
            },
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_TARGET_SOURCE: InputFieldInfo(
                    field_name=CONF_MAX_POWER_TARGET_SOURCE,
                    entity_description=NumberEntityDescription(
                        key=CONF_MAX_POWER_TARGET_SOURCE,
                        translation_key=f"{ELEMENT_TYPE}_{CONF_MAX_POWER_TARGET_SOURCE}",
                        native_unit_of_measurement=UnitOfMeasurement.KILO_WATT,
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
                CONF_MAX_POWER_SOURCE_TARGET: InputFieldInfo(
                    field_name=CONF_MAX_POWER_SOURCE_TARGET,
                    entity_description=NumberEntityDescription(
                        key=CONF_MAX_POWER_SOURCE_TARGET,
                        translation_key=f"{ELEMENT_TYPE}_{CONF_MAX_POWER_SOURCE_TARGET}",
                        native_unit_of_measurement=UnitOfMeasurement.KILO_WATT,
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
            },
            SECTION_LIMITS: {
                CONF_MIN_CHARGE_PERCENTAGE: InputFieldInfo(
                    field_name=CONF_MIN_CHARGE_PERCENTAGE,
                    entity_description=NumberEntityDescription(
                        key=CONF_MIN_CHARGE_PERCENTAGE,
                        translation_key=f"{ELEMENT_TYPE}_{CONF_MIN_CHARGE_PERCENTAGE}",
                        native_unit_of_measurement=UnitOfMeasurement.PERCENT,
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
                        native_unit_of_measurement=UnitOfMeasurement.PERCENT,
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
            SECTION_EFFICIENCY: {
                CONF_EFFICIENCY_SOURCE_TARGET: InputFieldInfo(
                    field_name=CONF_EFFICIENCY_SOURCE_TARGET,
                    entity_description=NumberEntityDescription(
                        key=CONF_EFFICIENCY_SOURCE_TARGET,
                        translation_key=f"{ELEMENT_TYPE}_{CONF_EFFICIENCY_SOURCE_TARGET}",
                        native_unit_of_measurement=UnitOfMeasurement.PERCENT,
                        device_class=NumberDeviceClass.POWER_FACTOR,
                        native_min_value=50.0,
                        native_max_value=100.0,
                        native_step=0.1,
                    ),
                    output_type=OutputType.EFFICIENCY,
                    time_series=True,
                    defaults=InputFieldDefaults(mode="value", value=95.0),
                ),
                CONF_EFFICIENCY_TARGET_SOURCE: InputFieldInfo(
                    field_name=CONF_EFFICIENCY_TARGET_SOURCE,
                    entity_description=NumberEntityDescription(
                        key=CONF_EFFICIENCY_TARGET_SOURCE,
                        translation_key=f"{ELEMENT_TYPE}_{CONF_EFFICIENCY_TARGET_SOURCE}",
                        native_unit_of_measurement=UnitOfMeasurement.PERCENT,
                        device_class=NumberDeviceClass.POWER_FACTOR,
                        native_min_value=50.0,
                        native_max_value=100.0,
                        native_step=0.1,
                    ),
                    output_type=OutputType.EFFICIENCY,
                    time_series=True,
                    defaults=InputFieldDefaults(mode="value", value=95.0),
                ),
            },
            SECTION_PRICING: {
                CONF_PRICE_SOURCE_TARGET: InputFieldInfo(
                    field_name=CONF_PRICE_SOURCE_TARGET,
                    entity_description=NumberEntityDescription(
                        key=CONF_PRICE_SOURCE_TARGET,
                        translation_key=f"{ELEMENT_TYPE}_{CONF_PRICE_SOURCE_TARGET}",
                        native_min_value=-1.0,
                        native_max_value=10.0,
                        native_step=0.001,
                    ),
                    output_type=OutputType.PRICE,
                    direction="-",
                    time_series=True,
                    defaults=InputFieldDefaults(mode=None, value=0.0),
                ),
                CONF_PRICE_TARGET_SOURCE: InputFieldInfo(
                    field_name=CONF_PRICE_TARGET_SOURCE,
                    entity_description=NumberEntityDescription(
                        key=CONF_PRICE_TARGET_SOURCE,
                        translation_key=f"{ELEMENT_TYPE}_{CONF_PRICE_TARGET_SOURCE}",
                        native_min_value=-1.0,
                        native_max_value=10.0,
                        native_step=0.001,
                    ),
                    output_type=OutputType.PRICE,
                    direction="-",
                    time_series=True,
                    defaults=InputFieldDefaults(mode=None, value=0.0),
                ),
                CONF_SALVAGE_VALUE: InputFieldInfo(
                    field_name=CONF_SALVAGE_VALUE,
                    entity_description=NumberEntityDescription(
                        key=CONF_SALVAGE_VALUE,
                        translation_key=f"{ELEMENT_TYPE}_{CONF_SALVAGE_VALUE}",
                        native_min_value=-1.0,
                        native_max_value=10.0,
                        native_step=0.001,
                    ),
                    output_type=OutputType.PRICE,
                    time_series=False,
                    defaults=InputFieldDefaults(mode=None, value=0.0),
                ),
            },
            SECTION_UNDERCHARGE: _partition_input_fields(
                percentage_default=0,
                cost_default=0,
                cost_direction="-",
            ),
            SECTION_OVERCHARGE: _partition_input_fields(
                percentage_default=100,
                cost_default=0,
                cost_direction="-",
            ),
        }

    def model_elements(self, config: BatteryConfigData) -> list[ModelElementConfig]:
        """Create model elements for Battery configuration.

        Creates a single battery element and a connection to the target.
        """
        common = config[SECTION_COMMON]
        storage = config[SECTION_STORAGE]
        limits = config[SECTION_LIMITS]
        power_limits = config[SECTION_POWER_LIMITS]
        pricing = config[SECTION_PRICING]
        efficiency_section = config[SECTION_EFFICIENCY]
        undercharge = config.get(SECTION_UNDERCHARGE, {})
        overcharge = config.get(SECTION_OVERCHARGE, {})

        name = common["name"]
        elements: list[ModelElementConfig] = []
        # capacity is boundaries (n+1 values), so n_periods = len - 1
        n_boundaries = len(storage[CONF_CAPACITY])
        n_periods = n_boundaries - 1

        capacity = storage[CONF_CAPACITY]
        capacity_first = float(capacity[0])
        initial_soc = storage[CONF_INITIAL_CHARGE_PERCENTAGE]

        min_charge_percentage = limits.get(CONF_MIN_CHARGE_PERCENTAGE, DEFAULTS[CONF_MIN_CHARGE_PERCENTAGE])
        max_charge_percentage = limits.get(CONF_MAX_CHARGE_PERCENTAGE, DEFAULTS[CONF_MAX_CHARGE_PERCENTAGE])
        efficiency_source_target = efficiency_section.get(CONF_EFFICIENCY_SOURCE_TARGET)
        efficiency_target_source = efficiency_section.get(CONF_EFFICIENCY_TARGET_SOURCE)

        undercharge_cost = undercharge.get(CONF_PARTITION_COST)
        overcharge_cost = overcharge.get(CONF_PARTITION_COST)
        undercharge_percentage = undercharge.get(CONF_PARTITION_PERCENTAGE) if undercharge_cost is not None else None
        overcharge_percentage = overcharge.get(CONF_PARTITION_PERCENTAGE) if overcharge_cost is not None else None

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
                "salvage_value": pricing.get(CONF_SALVAGE_VALUE, 0.0),
            }
        )

        # Create connection from battery to target
        price_source_target = pricing.get(CONF_PRICE_SOURCE_TARGET)
        price_target_source = pricing.get(CONF_PRICE_TARGET_SOURCE)
        charge_early_incentive = _build_charge_early_incentive(price_target_source, n_periods)
        discharge_pricing = _build_discharge_pricing(price_source_target, price_target_source, n_periods)
        max_discharge = power_limits.get(CONF_MAX_POWER_SOURCE_TARGET)
        max_charge = power_limits.get(CONF_MAX_POWER_TARGET_SOURCE)

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
            "power_limit": {
                "segment_type": "power_limit",
                "max_power_source_target": max_discharge,
                "max_power_target_source": max_charge,
            },
            "pricing": {
                "segment_type": "pricing",
                "price_source_target": discharge_pricing,
                "price_target_source": charge_early_incentive,
            },
            "efficiency": {
                "segment_type": "efficiency",
                "efficiency_source_target": efficiency_source_target,  # Battery to network (discharge)
                "efficiency_target_source": efficiency_target_source,  # Network to battery (charge)
            },
        }
        if soc_pricing_spec is not None:
            segments["soc_pricing"] = soc_pricing_spec

        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:connection",
                "source": name,
                "target": extract_connection_target(common[CONF_CONNECTION]),
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


def _build_charge_early_incentive(
    value: NDArray[np.floating[Any]] | float | None,
    n_periods: int,
) -> NDArray[np.float64] | None:
    """Build the decaying charge incentive series."""
    if value is None or n_periods <= 0:
        return None

    values = broadcast_to_sequence(value, n_periods)
    ramp = np.arange(n_periods, dtype=np.float64) / max(n_periods - 1, 1)
    return values * (ramp - 1.0)


def _build_discharge_pricing(
    price_source_target: NDArray[np.floating[Any]] | float | None,
    early_charge_incentive: NDArray[np.floating[Any]] | float | None,
    n_periods: int,
) -> NDArray[np.float64] | None:
    """Build discharge pricing with early incentive ramp."""
    if n_periods <= 0:
        return None

    base = broadcast_to_sequence(price_source_target, n_periods) if price_source_target is not None else None
    if early_charge_incentive is None:
        return base

    incentive = broadcast_to_sequence(early_charge_incentive, n_periods)
    ramp = np.arange(n_periods, dtype=np.float64) / max(n_periods - 1, 1)
    discharge_incentive = incentive * (1.0 + ramp)
    if base is None:
        return discharge_incentive
    return base + discharge_incentive


def _partition_input_fields(
    *,
    percentage_default: int,
    cost_default: int,
    cost_direction: str,
) -> dict[str, InputFieldInfo[Any]]:
    """Build shared input field definitions for partition sections."""
    return {
        CONF_PARTITION_PERCENTAGE: InputFieldInfo(
            field_name=CONF_PARTITION_PERCENTAGE,
            entity_description=NumberEntityDescription(
                key=CONF_PARTITION_PERCENTAGE,
                translation_key=f"{ELEMENT_TYPE}_{CONF_PARTITION_PERCENTAGE}",
                native_unit_of_measurement=UnitOfMeasurement.PERCENT,
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
        CONF_PARTITION_COST: InputFieldInfo(
            field_name=CONF_PARTITION_COST,
            entity_description=NumberEntityDescription(
                key=CONF_PARTITION_COST,
                translation_key=f"{ELEMENT_TYPE}_{CONF_PARTITION_COST}",
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
    capacity = config[SECTION_STORAGE][CONF_CAPACITY]

    # Get time-varying min ratio (also boundaries)
    min_charge_percentage = config[SECTION_LIMITS].get(
        CONF_MIN_CHARGE_PERCENTAGE,
        DEFAULTS[CONF_MIN_CHARGE_PERCENTAGE],
    )
    undercharge = config.get(SECTION_UNDERCHARGE, {})
    undercharge_cost = undercharge.get(CONF_PARTITION_COST)
    undercharge_pct = undercharge.get(CONF_PARTITION_PERCENTAGE) if undercharge_cost is not None else None
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
    capacity = config[SECTION_STORAGE][CONF_CAPACITY]
    soc_values = np.asarray(total_energy.values, dtype=float) / capacity

    return OutputData(
        type=OutputType.STATE_OF_CHARGE,
        unit="%",
        values=tuple(soc_values.tolist()),
    )
