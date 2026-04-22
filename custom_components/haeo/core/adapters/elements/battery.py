"""Battery element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

import numpy as np

from custom_components.haeo.core.adapters.output_utils import expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.elements import energy_storage as model_es
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_ENERGY_STORAGE
from custom_components.haeo.core.model.elements.energy_storage import InventoryCostSpec
from custom_components.haeo.core.model.elements.segments import SegmentSpec
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
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_INVENTORY_COSTS,
    CONF_SALVAGE_VALUE,
    CONF_THRESHOLD,
    ELEMENT_TYPE,
    SECTION_STORAGE,
    BatteryConfigData,
    InventoryCostData,
)
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)

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


def _build_inventory_costs(
    inventory_costs: list[InventoryCostData],
    capacity: Any,
    n_periods: int,
) -> list[InventoryCostSpec]:
    """Convert adapter-layer inventory cost data to model-layer specs.

    Thresholds in the config may be in kWh (absolute) or percentage of capacity.
    The model layer expects absolute kWh thresholds.
    """
    result: list[InventoryCostSpec] = []
    for ic in inventory_costs:
        threshold = ic[CONF_THRESHOLD]
        price = ic[CONF_COST]
        direction = ic[CONF_DIRECTION]

        threshold_array = broadcast_to_sequence(threshold, n_periods)
        price_array = broadcast_to_sequence(price, n_periods)

        result.append(
            InventoryCostSpec(
                direction=direction,
                threshold=threshold_array,
                price=price_array,
            )
        )
    return result


class BatteryAdapter:
    """Adapter for Battery elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.ADVANCED
    can_source: bool = True
    can_sink: bool = True

    def model_elements(self, config: BatteryConfigData) -> list[ModelElementConfig]:
        """Create model elements for Battery configuration.

        Creates a single energy storage element and connections to the target.
        """
        storage = config[SECTION_STORAGE]
        power_limits = config[SECTION_POWER_LIMITS]
        pricing = config[SECTION_PRICING]
        efficiency_section = config[SECTION_EFFICIENCY]

        name = config["name"]
        elements: list[ModelElementConfig] = []
        capacity = storage[CONF_CAPACITY]
        n_boundaries = len(capacity)
        n_periods = n_boundaries - 1
        capacity_first = float(capacity[0])
        initial_soc = storage[CONF_INITIAL_CHARGE_PERCENTAGE]

        initial_charge = initial_soc * capacity_first

        efficiency_source_target = efficiency_section.get(CONF_EFFICIENCY_SOURCE_TARGET)
        efficiency_target_source = efficiency_section.get(CONF_EFFICIENCY_TARGET_SOURCE)

        inventory_costs_data = config.get(CONF_INVENTORY_COSTS, [])
        inventory_cost_specs = (
            _build_inventory_costs(inventory_costs_data, capacity, n_periods)
            if inventory_costs_data
            else []
        )

        es_config: dict[str, Any] = {
            "element_type": MODEL_ELEMENT_TYPE_ENERGY_STORAGE,
            "name": name,
            "capacity": capacity,
            "initial_charge": initial_charge,
            "salvage_value": pricing.get(CONF_SALVAGE_VALUE, 0.0),
        }
        if inventory_cost_specs:
            es_config["inventory_costs"] = inventory_cost_specs

        elements.append(es_config)

        # Create connections
        max_discharge = power_limits.get(CONF_MAX_POWER_SOURCE_TARGET)
        max_charge = power_limits.get(CONF_MAX_POWER_TARGET_SOURCE)

        discharge_segments: dict[str, SegmentSpec] = {
            "efficiency": {"segment_type": "efficiency", "efficiency": efficiency_source_target},
            "power_limit": {"segment_type": "power_limit", "max_power": max_discharge},
        }

        # Discharge: energy_storage -> network
        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:discharge",
                "source": name,
                "target": extract_connection_target(config[CONF_CONNECTION]),
                "segments": discharge_segments,
            }
        )
        # Charge: network -> energy_storage
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
        """Map model outputs to battery-specific output names."""
        battery_outputs = {key: expect_output_data(value) for key, value in model_outputs[name].items()}

        power_charge = battery_outputs[model_es.BATTERY_POWER_CHARGE]
        power_discharge = battery_outputs[model_es.BATTERY_POWER_DISCHARGE]
        energy_stored = battery_outputs[model_es.BATTERY_ENERGY_STORED]

        aggregate_soc = _calculate_soc(energy_stored, config)

        aggregate_outputs: dict[BatteryOutputName, OutputData] = {
            BATTERY_POWER_CHARGE: power_charge,
            BATTERY_POWER_DISCHARGE: power_discharge,
            BATTERY_ENERGY_STORED: energy_stored,
            BATTERY_STATE_OF_CHARGE: aggregate_soc,
        }

        aggregate_outputs[BATTERY_POWER_ACTIVE] = replace(
            power_discharge,
            values=[d - c for d, c in zip(power_discharge.values, power_charge.values, strict=True)],
            direction=None,
            type=OutputType.POWER,
        )

        aggregate_outputs[BATTERY_POWER_BALANCE] = battery_outputs[model_es.BATTERY_POWER_BALANCE]
        aggregate_outputs[BATTERY_ENERGY_IN_FLOW] = replace(
            battery_outputs[model_es.BATTERY_ENERGY_IN_FLOW], advanced=True
        )
        aggregate_outputs[BATTERY_ENERGY_OUT_FLOW] = replace(
            battery_outputs[model_es.BATTERY_ENERGY_OUT_FLOW], advanced=True
        )
        aggregate_outputs[BATTERY_SOC_MAX] = replace(battery_outputs[model_es.BATTERY_SOC_MAX], advanced=True)
        aggregate_outputs[BATTERY_SOC_MIN] = replace(battery_outputs[model_es.BATTERY_SOC_MIN], advanced=True)

        return {BATTERY_DEVICE_BATTERY: aggregate_outputs}


adapter = BatteryAdapter()


def _calculate_soc(energy_stored: OutputData, config: BatteryConfigData) -> OutputData:
    """Calculate SOC ratio from stored energy and total capacity."""
    capacity = config[SECTION_STORAGE][CONF_CAPACITY]
    soc_values = np.asarray(energy_stored.values, dtype=float) / capacity

    return OutputData(
        type=OutputType.STATE_OF_CHARGE,
        unit="%",
        values=tuple(soc_values.tolist()),
    )
