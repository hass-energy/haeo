"""Solar element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import ConstantLoader, TimeSeriesLoader
from custom_components.haeo.elements.input_fields import InputFieldDefaults, InputFieldInfo
from custom_components.haeo.model import ModelElementConfig, ModelOutputName
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.model.elements.power_connection import (
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
)
from custom_components.haeo.model.output_data import OutputData

from .schema import (
    CONF_CONNECTION,
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_PRODUCTION,
    ELEMENT_TYPE,
    SolarConfigData,
    SolarConfigSchema,
)

# Default values for optional fields applied by adapter
DEFAULTS: Final[dict[str, bool | float]] = {
    CONF_CURTAILMENT: True,  # Allow curtailment by default
    CONF_PRICE_PRODUCTION: 0.0,  # No production incentive
}

# Solar output names
type SolarOutputName = Literal[
    "solar_power",
    "solar_forecast_limit",
]

SOLAR_OUTPUT_NAMES: Final[frozenset[SolarOutputName]] = frozenset(
    (
        SOLAR_POWER := "solar_power",
        # Shadow price
        SOLAR_FORECAST_LIMIT := "solar_forecast_limit",
    )
)

type SolarDeviceName = Literal["solar"]

SOLAR_DEVICE_NAMES: Final[frozenset[SolarDeviceName]] = frozenset((SOLAR_DEVICE_SOLAR := "solar",))


class SolarAdapter:
    """Adapter for Solar elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.ADVANCED

    def available(self, config: SolarConfigSchema, *, hass: HomeAssistant, **_kwargs: Any) -> bool:
        """Check if solar configuration can be loaded."""
        ts_loader = TimeSeriesLoader()
        return ts_loader.available(hass=hass, value=config[CONF_FORECAST])

    def inputs(self, config: Any) -> tuple[InputFieldInfo[Any], ...]:
        """Return input field definitions for solar elements."""
        _ = config
        return (
            InputFieldInfo(
                field_name=CONF_FORECAST,
                entity_description=NumberEntityDescription(
                    key=CONF_FORECAST,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_FORECAST}",
                    native_unit_of_measurement=UnitOfPower.KILO_WATT,
                    device_class=NumberDeviceClass.POWER,
                    native_min_value=0.0,
                    native_max_value=1000.0,
                    native_step=0.01,
                ),
                output_type=OutputType.POWER,
                direction="-",
                time_series=True,
            ),
            InputFieldInfo(
                field_name=CONF_PRICE_PRODUCTION,
                entity_description=NumberEntityDescription(
                    key=CONF_PRICE_PRODUCTION,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_PRICE_PRODUCTION}",
                    native_min_value=-1.0,
                    native_max_value=10.0,
                    native_step=0.001,
                ),
                output_type=OutputType.PRICE,
                direction="+",
                defaults=InputFieldDefaults(mode=None, value=0.0),
            ),
            InputFieldInfo(
                field_name=CONF_CURTAILMENT,
                entity_description=SwitchEntityDescription(
                    key=CONF_CURTAILMENT,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_CURTAILMENT}",
                ),
                output_type=OutputType.STATUS,
                defaults=InputFieldDefaults(mode="value", value=True),
                force_required=True,
            ),
        )

    def build_config_data(
        self,
        loaded_values: Mapping[str, Any],
        config: SolarConfigSchema,
    ) -> SolarConfigData:
        """Build ConfigData from pre-loaded values.

        This is the single source of truth for ConfigData construction.
        Both load() and the coordinator use this method.

        Args:
            loaded_values: Dict of field names to loaded values (from input entities or TimeSeriesLoader)
            config: Original ConfigSchema for non-input fields (element_type, name, connection)

        Returns:
            SolarConfigData with all fields populated

        """
        data: SolarConfigData = {
            "element_type": config["element_type"],
            "name": config["name"],
            "connection": config[CONF_CONNECTION],
            "forecast": list(loaded_values[CONF_FORECAST]),
        }

        # Optional scalar fields
        if CONF_PRICE_PRODUCTION in loaded_values:
            data["price_production"] = float(loaded_values[CONF_PRICE_PRODUCTION])
        if CONF_CURTAILMENT in loaded_values:
            data["curtailment"] = bool(loaded_values[CONF_CURTAILMENT])

        return data

    async def load(
        self,
        config: SolarConfigSchema,
        *,
        hass: HomeAssistant,
        forecast_times: Sequence[float],
    ) -> SolarConfigData:
        """Load solar configuration values from sensors.

        Uses TimeSeriesLoader to load values, then delegates to build_config_data().
        """
        ts_loader = TimeSeriesLoader()
        const_loader_float = ConstantLoader[float](float)
        const_loader_bool = ConstantLoader[bool](bool)
        loaded_values: dict[str, list[float] | float | bool] = {}

        # Load required time series field
        loaded_values[CONF_FORECAST] = await ts_loader.load_intervals(
            hass=hass, value=config[CONF_FORECAST], forecast_times=forecast_times
        )

        # Load optional scalar fields
        if CONF_PRICE_PRODUCTION in config:
            loaded_values[CONF_PRICE_PRODUCTION] = await const_loader_float.load(value=config[CONF_PRICE_PRODUCTION])
        if CONF_CURTAILMENT in config:
            loaded_values[CONF_CURTAILMENT] = await const_loader_bool.load(value=config[CONF_CURTAILMENT])

        return self.build_config_data(loaded_values, config)

    def model_elements(self, config: SolarConfigData) -> list[ModelElementConfig]:
        """Return model element parameters for Solar configuration."""
        return [
            {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": config["name"], "is_source": True, "is_sink": False},
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{config['name']}:connection",
                "source": config["name"],
                "target": config["connection"],
                "max_power_source_target": config["forecast"],
                "max_power_target_source": 0.0,
                "fixed_power": not config.get("curtailment", DEFAULTS[CONF_CURTAILMENT]),
                "price_source_target": config.get("price_production"),
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]],
        **_kwargs: Any,
    ) -> Mapping[SolarDeviceName, Mapping[SolarOutputName, OutputData]]:
        """Map model outputs to solar-specific output names."""
        connection = model_outputs[f"{name}:connection"]

        solar_outputs: dict[SolarOutputName, OutputData] = {
            SOLAR_POWER: replace(connection[CONNECTION_POWER_SOURCE_TARGET], type=OutputType.POWER),
            SOLAR_FORECAST_LIMIT: connection[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET],
        }

        return {SOLAR_DEVICE_SOLAR: solar_outputs}


adapter = SolarAdapter()
