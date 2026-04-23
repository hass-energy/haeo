"""Battery element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

import numpy as np

from custom_components.haeo.core.adapters.output_utils import expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model import battery as model_battery
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_BATTERY, MODEL_ELEMENT_TYPE_CONNECTION
from custom_components.haeo.core.model.elements.segments import SegmentSpec, SocPricingSegmentSpec
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.util import broadcast_to_sequence
from custom_components.haeo.core.schema import extract_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.battery import (
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
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
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
    can_source: bool = True
    can_sink: bool = True

    def model_elements(self, config: BatteryConfigData) -> list[ModelElementConfig]:
        """Create model elements for Battery configuration.

        Creates a single battery element and a connection to the target.
        """
        storage = config[SECTION_STORAGE]
        limits = config[SECTION_LIMITS]
        power_limits = config[SECTION_POWER_LIMITS]
        pricing = config[SECTION_PRICING]
        efficiency_section = config[SECTION_EFFICIENCY]
        undercharge = config.get(SECTION_UNDERCHARGE, {})
        overcharge = config.get(SECTION_OVERCHARGE, {})

        name = config["name"]
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

        discharge_segments: dict[str, SegmentSpec] = {
            "efficiency": {"segment_type": "efficiency", "efficiency": efficiency_source_target},
            "power_limit": {"segment_type": "power_limit", "max_power": max_discharge},
        }
        if soc_pricing_spec is not None:
            discharge_segments["soc_pricing"] = soc_pricing_spec

        # Discharge: battery -> network
        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:discharge",
                "source": name,
                "target": extract_connection_target(config[CONF_CONNECTION]),
                "segments": discharge_segments,
            }
        )
        # Charge: network -> battery
        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:charge",
                "source": extract_connection_target(config[CONF_CONNECTION]),
                "target": name,
                "segments": {
                    "efficiency": {"segment_type": "efficiency", "efficiency": efficiency_target_source},
                    "power_limit": {"segment_type": "power_limit", "max_power": max_charge},
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
