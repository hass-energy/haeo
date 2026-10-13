"""Battery element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Final, Literal

import numpy as np

from custom_components.haeo.core.adapters.output_utils import connection_power, expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model import battery as model_battery
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_HOLDING_COST,
)
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.util import broadcast_to_sequence
from custom_components.haeo.core.schema import extract_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_COST,
    CONF_DIRECTION,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_ENABLED,
    CONF_HOLDING_COSTS,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_SALVAGE_VALUE,
    CONF_THRESHOLD,
    ELEMENT_TYPE,
    SECTION_LIMITS,
    SECTION_STORAGE,
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
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER
    can_source: bool = True
    can_sink: bool = True

    def model_elements(self, config: BatteryConfigData) -> list[ModelElementConfig]:
        """Create model elements for Battery configuration.

        Creates a battery element whose stored energy is measured from the minimum
        charge level, a connection in each direction to the target, and a holding
        cost element for each holding cost.
        """
        storage = config[SECTION_STORAGE]
        limits = config[SECTION_LIMITS]
        power_limits = config[SECTION_POWER_LIMITS]
        pricing = config[SECTION_PRICING]
        efficiency_section = config[SECTION_EFFICIENCY]

        name = config["name"]
        # capacity is boundaries (n+1 values), so n_periods = len - 1
        capacity = storage[CONF_CAPACITY]
        n_boundaries = len(capacity)
        initial_soc = storage[CONF_INITIAL_CHARGE_PERCENTAGE]

        min_ratio = broadcast_to_sequence(
            limits.get(CONF_MIN_CHARGE_PERCENTAGE, DEFAULTS[CONF_MIN_CHARGE_PERCENTAGE]), n_boundaries
        )
        max_ratio = broadcast_to_sequence(
            limits.get(CONF_MAX_CHARGE_PERCENTAGE, DEFAULTS[CONF_MAX_CHARGE_PERCENTAGE]), n_boundaries
        )
        capacity_range = (max_ratio - min_ratio) * capacity
        initial_charge = max(
            min((initial_soc - float(min_ratio[0])) * float(capacity[0]), float(capacity_range[0])), 0.0
        )

        elements: list[ModelElementConfig] = [
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": name,
                "capacity": capacity_range,
                "initial_charge": initial_charge,
                "salvage_value": pricing.get(CONF_SALVAGE_VALUE, 0.0),
            }
        ]

        # Efficiency sits next to the battery and the power limit at the bus end,
        # where the battery terminals are metered, in both directions.
        # Discharge: battery -> network
        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:discharge",
                "source": name,
                "target": extract_connection_target(config[CONF_CONNECTION]),
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency": efficiency_section.get(CONF_EFFICIENCY_SOURCE_TARGET),
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power": power_limits.get(CONF_MAX_POWER_SOURCE_TARGET),
                    },
                },
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
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power": power_limits.get(CONF_MAX_POWER_TARGET_SOURCE),
                    },
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency": efficiency_section.get(CONF_EFFICIENCY_TARGET_SOURCE),
                    },
                },
            }
        )

        # Thresholds are measured in the battery's coordinate, from the minimum charge level,
        # at the end of each period. A disabled holding cost keeps its element at a zero price,
        # so switching it back on updates a price rather than changing the network.
        elements.extend(
            {
                "element_type": MODEL_ELEMENT_TYPE_HOLDING_COST,
                "name": f"{name}:holding_cost:{index}",
                "storage": name,
                "direction": holding_cost[CONF_DIRECTION],
                "threshold": ((holding_cost[CONF_THRESHOLD] - min_ratio) * capacity)[1:],
                "price": holding_cost[CONF_COST] if holding_cost[CONF_ENABLED] else np.zeros(n_boundaries - 1),
            }
            for index, holding_cost in enumerate(config.get(CONF_HOLDING_COSTS, []))
        )

        return elements

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        config: BatteryConfigData,
        **_kwargs: object,
    ) -> Mapping[BatteryDeviceName, Mapping[BatteryOutputName, OutputData]]:
        """Map model outputs to battery-specific output names."""
        discharge_conn = model_outputs.get(f"{name}:discharge")
        charge_conn = model_outputs.get(f"{name}:charge")
        period_count = len(expect_output_data(model_outputs[name][model_battery.BATTERY_POWER_CHARGE]).values)

        # Each connection reports power at its measured point, where its power limit
        # applies: the battery terminals.
        power_discharge = replace(connection_power(discharge_conn, period_count), type=OutputType.POWER)
        power_charge = replace(connection_power(charge_conn, period_count), type=OutputType.POWER, direction="-")

        # Battery-internal outputs (energy, SOC, shadow prices)
        battery_outputs = {key: expect_output_data(value) for key, value in model_outputs[name].items()}
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
    min_charge_percentage = config[SECTION_LIMITS].get(
        CONF_MIN_CHARGE_PERCENTAGE,
        DEFAULTS[CONF_MIN_CHARGE_PERCENTAGE],
    )

    # Both energy values and capacity/ratios are boundaries (n+1 values)
    inaccessible_energy = min_charge_percentage * capacity
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
