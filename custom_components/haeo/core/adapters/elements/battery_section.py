"""Battery section element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.adapters.output_utils import expect_output_data
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model import battery as model_battery
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_BATTERY
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.battery_section import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE,
    ELEMENT_TYPE,
    SECTION_STORAGE,
    BatterySectionConfigData,
)
from custom_components.haeo.core.schema.sections import SECTION_COMMON

type BatterySectionOutputName = Literal[
    "battery_section_power_charge",
    "battery_section_power_discharge",
    "battery_section_power_active",
    "battery_section_energy_stored",
    "battery_section_power_balance",
    "battery_section_energy_in_flow",
    "battery_section_energy_out_flow",
    "battery_section_soc_max",
    "battery_section_soc_min",
]

BATTERY_SECTION_OUTPUT_NAMES: Final[frozenset[BatterySectionOutputName]] = frozenset(
    (
        BATTERY_SECTION_POWER_CHARGE := "battery_section_power_charge",
        BATTERY_SECTION_POWER_DISCHARGE := "battery_section_power_discharge",
        BATTERY_SECTION_POWER_ACTIVE := "battery_section_power_active",
        BATTERY_SECTION_ENERGY_STORED := "battery_section_energy_stored",
        BATTERY_SECTION_POWER_BALANCE := "battery_section_power_balance",
        BATTERY_SECTION_ENERGY_IN_FLOW := "battery_section_energy_in_flow",
        BATTERY_SECTION_ENERGY_OUT_FLOW := "battery_section_energy_out_flow",
        BATTERY_SECTION_SOC_MAX := "battery_section_soc_max",
        BATTERY_SECTION_SOC_MIN := "battery_section_soc_min",
    )
)

type BatterySectionDeviceName = Literal[ElementType.BATTERY_SECTION]

BATTERY_SECTION_DEVICE_NAMES: Final[frozenset[BatterySectionDeviceName]] = frozenset(
    (BATTERY_SECTION_DEVICE := ElementType.BATTERY_SECTION,),
)


class BatterySectionAdapter:
    """Adapter for Battery Section elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = True
    connectivity: ConnectivityLevel = ConnectivityLevel.ADVANCED

    def model_elements(self, config: BatterySectionConfigData) -> list[ModelElementConfig]:
        """Create model elements for BatterySection configuration.

        Direct pass-through to the model battery element.
        """
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": config[SECTION_COMMON]["name"],
                "capacity": config[SECTION_STORAGE][CONF_CAPACITY],
                "initial_charge": config[SECTION_STORAGE][CONF_INITIAL_CHARGE][0],
            }
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: Any,
    ) -> Mapping[BatterySectionDeviceName, Mapping[BatterySectionOutputName, OutputData]]:
        """Map model outputs to battery section output names."""
        battery_data = {key: expect_output_data(value) for key, value in model_outputs[name].items()}

        section_outputs: dict[BatterySectionOutputName, OutputData] = {}

        # Power outputs
        section_outputs[BATTERY_SECTION_POWER_CHARGE] = replace(
            battery_data[model_battery.BATTERY_POWER_CHARGE], type=OutputType.POWER
        )
        section_outputs[BATTERY_SECTION_POWER_DISCHARGE] = replace(
            battery_data[model_battery.BATTERY_POWER_DISCHARGE], type=OutputType.POWER
        )

        # Active power (discharge - charge)
        charge_values = battery_data[model_battery.BATTERY_POWER_CHARGE].values
        discharge_values = battery_data[model_battery.BATTERY_POWER_DISCHARGE].values
        section_outputs[BATTERY_SECTION_POWER_ACTIVE] = replace(
            battery_data[model_battery.BATTERY_POWER_CHARGE],
            values=[d - c for c, d in zip(charge_values, discharge_values, strict=True)],
            direction=None,
            type=OutputType.POWER,
        )

        # Energy stored
        section_outputs[BATTERY_SECTION_ENERGY_STORED] = battery_data[model_battery.BATTERY_ENERGY_STORED]

        # Shadow prices
        if model_battery.BATTERY_POWER_BALANCE in battery_data:
            section_outputs[BATTERY_SECTION_POWER_BALANCE] = battery_data[model_battery.BATTERY_POWER_BALANCE]
        if model_battery.BATTERY_ENERGY_IN_FLOW in battery_data:
            section_outputs[BATTERY_SECTION_ENERGY_IN_FLOW] = battery_data[model_battery.BATTERY_ENERGY_IN_FLOW]
        if model_battery.BATTERY_ENERGY_OUT_FLOW in battery_data:
            section_outputs[BATTERY_SECTION_ENERGY_OUT_FLOW] = battery_data[model_battery.BATTERY_ENERGY_OUT_FLOW]
        if model_battery.BATTERY_SOC_MAX in battery_data:
            section_outputs[BATTERY_SECTION_SOC_MAX] = battery_data[model_battery.BATTERY_SOC_MAX]
        if model_battery.BATTERY_SOC_MIN in battery_data:
            section_outputs[BATTERY_SECTION_SOC_MIN] = battery_data[model_battery.BATTERY_SOC_MIN]

        return {BATTERY_SECTION_DEVICE: section_outputs}


adapter = BatterySectionAdapter()
