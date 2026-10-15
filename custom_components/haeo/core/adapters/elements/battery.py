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
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_BATTERY, MODEL_ELEMENT_TYPE_CONNECTION
from custom_components.haeo.core.model.elements.segments import SegmentSpec
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import extract_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_SALVAGE_VALUE,
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

        Creates a single battery element and a connection to the target. The
        battery holds energy between empty and its capacity, with its min and max
        charge kept as priced limits, so a reported charge outside them still
        gives a feasible plan.
        """
        storage = config[SECTION_STORAGE]
        power_limits = config[SECTION_POWER_LIMITS]
        efficiency_section = config[SECTION_EFFICIENCY]

        name = config["name"]
        capacity = storage[CONF_CAPACITY]
        capacity_first = float(capacity[0])
        initial_charge = min(max(storage[CONF_INITIAL_CHARGE_PERCENTAGE] * capacity_first, 0.0), capacity_first)

        battery: model_battery.BatteryElementConfig = {
            "element_type": MODEL_ELEMENT_TYPE_BATTERY,
            "name": name,
            "capacity": capacity,
            "initial_charge": initial_charge,
            "salvage_value": config[SECTION_PRICING].get(CONF_SALVAGE_VALUE, 0.0),
        }
        # Unset limits leave the battery free to run from empty to full
        limits = config[SECTION_LIMITS]
        if (min_ratio := limits.get(CONF_MIN_CHARGE_PERCENTAGE)) is not None:
            battery["min_charge"] = min_ratio * capacity
        if (max_ratio := limits.get(CONF_MAX_CHARGE_PERCENTAGE)) is not None:
            battery["max_charge"] = max_ratio * capacity
        elements: list[ModelElementConfig] = [battery]

        max_discharge = power_limits.get(CONF_MAX_POWER_SOURCE_TARGET)
        max_charge = power_limits.get(CONF_MAX_POWER_TARGET_SOURCE)
        efficiency_source_target = efficiency_section.get(CONF_EFFICIENCY_SOURCE_TARGET)
        efficiency_target_source = efficiency_section.get(CONF_EFFICIENCY_TARGET_SOURCE)

        # Efficiency sits next to the battery and the power limit at the bus end,
        # where the battery terminals are metered, in both directions.
        discharge_segments: dict[str, SegmentSpec] = {
            "efficiency": {"segment_type": "efficiency", "efficiency": efficiency_source_target},
            "power_limit": {"segment_type": "power_limit", "max_power": max_discharge},
        }

        # Discharge: battery -> network
        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": discharge_connection_name(name),
                "source": name,
                "target": extract_connection_target(config[CONF_CONNECTION]),
                "segments": discharge_segments,
            }
        )
        # Charge: network -> battery
        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": charge_connection_name(name),
                "source": extract_connection_target(config[CONF_CONNECTION]),
                "target": name,
                "segments": {
                    "power_limit": {"segment_type": "power_limit", "max_power": max_charge},
                    "efficiency": {"segment_type": "efficiency", "efficiency": efficiency_target_source},
                },
            }
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
        discharge_conn = model_outputs.get(discharge_connection_name(name))
        charge_conn = model_outputs.get(charge_connection_name(name))
        period_count = len(expect_output_data(model_outputs[name][model_battery.BATTERY_POWER_CHARGE]).values)

        # Each connection reports power at its measured point, where its power limit
        # applies: the battery terminals.
        power_discharge = replace(connection_power(discharge_conn, period_count), type=OutputType.POWER)
        power_charge = replace(connection_power(charge_conn, period_count), type=OutputType.POWER, direction="-")

        # Battery-internal outputs (energy, SOC, shadow prices)
        battery_outputs = {key: expect_output_data(value) for key, value in model_outputs[name].items()}
        energy_stored = battery_outputs[model_battery.BATTERY_ENERGY_STORED]

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


def discharge_connection_name(name: str) -> str:
    """Return the name of the connection a battery discharges through."""
    return f"{name}:discharge"


def charge_connection_name(name: str) -> str:
    """Return the name of the connection a battery charges through."""
    return f"{name}:charge"


def _calculate_soc(total_energy: OutputData, config: BatteryConfigData) -> OutputData:
    """Calculate SOC ratio from stored energy and capacity."""
    # Capacity is already boundaries (n+1 values), same as energy
    capacity = config[SECTION_STORAGE][CONF_CAPACITY]
    soc_values = np.asarray(total_energy.values, dtype=float) / capacity

    return OutputData(
        type=OutputType.STATE_OF_CHARGE,
        unit="%",
        values=tuple(soc_values.tolist()),
    )
