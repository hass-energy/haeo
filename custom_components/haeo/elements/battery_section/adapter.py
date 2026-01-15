"""Battery section element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.core import HomeAssistant

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.model import battery as model_battery
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_BATTERY
from custom_components.haeo.model.output_data import OutputData

from .flow import BatterySectionSubentryFlowHandler
from .schema import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE,
    ELEMENT_TYPE,
    BatterySectionConfigData,
    BatterySectionConfigSchema,
)

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

type BatterySectionDeviceName = Literal["battery_section"]

BATTERY_SECTION_DEVICE_NAMES: Final[frozenset[BatterySectionDeviceName]] = frozenset(
    (BATTERY_SECTION_DEVICE := "battery_section",),
)


class BatterySectionAdapter:
    """Adapter for Battery Section elements."""

    element_type: str = ELEMENT_TYPE
    flow_class: type = BatterySectionSubentryFlowHandler
    advanced: bool = True
    connectivity: ConnectivityLevel = ConnectivityLevel.ADVANCED

    def available(self, config: BatterySectionConfigSchema, *, hass: HomeAssistant, **_kwargs: Any) -> bool:
        """Check if battery section configuration can be loaded."""
        ts_loader = TimeSeriesLoader()

        # Check required time series fields
        required_fields = [CONF_CAPACITY, CONF_INITIAL_CHARGE]
        return all(ts_loader.available(hass=hass, value=config[field]) for field in required_fields)

    def build_config_data(
        self,
        loaded_values: Mapping[str, Any],
        config: BatterySectionConfigSchema,
    ) -> BatterySectionConfigData:
        """Build ConfigData from pre-loaded values.

        This is the single source of truth for ConfigData construction.
        Both load() and the coordinator use this method.

        Args:
            loaded_values: Dict of field names to loaded values (from input entities or TimeSeriesLoader)
            config: Original ConfigSchema for non-input fields (element_type, name)

        Returns:
            BatterySectionConfigData with all fields populated

        """
        return {
            "element_type": config["element_type"],
            "name": config["name"],
            "capacity": list(loaded_values[CONF_CAPACITY]),
            "initial_charge": list(loaded_values[CONF_INITIAL_CHARGE]),
        }

    async def load(
        self,
        config: BatterySectionConfigSchema,
        *,
        hass: HomeAssistant,
        forecast_times: Sequence[float],
    ) -> BatterySectionConfigData:
        """Load battery section configuration values from sensors.

        Uses TimeSeriesLoader to load values, then delegates to build_config_data().
        """
        ts_loader = TimeSeriesLoader()
        loaded_values: dict[str, list[float]] = {}

        loaded_values[CONF_CAPACITY] = await ts_loader.load_boundaries(
            hass=hass, value=config[CONF_CAPACITY], forecast_times=forecast_times
        )
        loaded_values[CONF_INITIAL_CHARGE] = await ts_loader.load_intervals(
            hass=hass, value=config[CONF_INITIAL_CHARGE], forecast_times=forecast_times
        )

        return self.build_config_data(loaded_values, config)

    def model_elements(self, config: BatterySectionConfigData) -> list[ModelElementConfig]:
        """Create model elements for BatterySection configuration.

        Direct pass-through to the model battery element.
        """
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": config["name"],
                "capacity": config["capacity"],
                "initial_charge": config["initial_charge"][0],
            }
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: Any,
    ) -> Mapping[BatterySectionDeviceName, Mapping[BatterySectionOutputName, OutputData]]:
        """Map model outputs to battery section output names."""
        battery_data = model_outputs[name]

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
