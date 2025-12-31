"""Solar element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.core import HomeAssistant

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import ConstantLoader, TimeSeriesLoader
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.const import OUTPUT_TYPE_POWER
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.power_connection import (
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
)

from .flow import SolarSubentryFlowHandler
from .schema import (
    CONF_CONNECTION,
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_PRODUCTION,
    DEFAULTS,
    ELEMENT_TYPE,
    SolarConfigData,
    SolarConfigSchema,
)

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
    flow_class: type = SolarSubentryFlowHandler
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.ADVANCED

    def available(self, config: SolarConfigSchema, *, hass: HomeAssistant, **_kwargs: Any) -> bool:
        """Check if solar configuration can be loaded."""
        ts_loader = TimeSeriesLoader()
        return ts_loader.available(hass=hass, value=config[CONF_FORECAST])

    async def load(
        self,
        config: SolarConfigSchema,
        *,
        hass: HomeAssistant,
        forecast_times: Sequence[float],
    ) -> SolarConfigData:
        """Load solar configuration values from sensors."""
        ts_loader = TimeSeriesLoader()
        const_loader_float = ConstantLoader[float](float)
        const_loader_bool = ConstantLoader[bool](bool)

        forecast = await ts_loader.load(
            hass=hass,
            value=config[CONF_FORECAST],
            forecast_times=forecast_times,
        )

        data: SolarConfigData = {
            "element_type": config["element_type"],
            "name": config["name"],
            "connection": config[CONF_CONNECTION],
            "forecast": forecast,
        }

        # Load optional fields
        if CONF_PRICE_PRODUCTION in config:
            data["price_production"] = await const_loader_float.load(value=config[CONF_PRICE_PRODUCTION])
        if CONF_CURTAILMENT in config:
            data["curtailment"] = await const_loader_bool.load(value=config[CONF_CURTAILMENT])

        return data

    def create_model_elements(self, config: SolarConfigData) -> list[dict[str, Any]]:
        """Create model elements for Solar configuration."""
        return [
            {"element_type": "node", "name": config["name"], "is_source": True, "is_sink": False},
            {
                "element_type": "connection",
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
        _config: SolarConfigData,
    ) -> Mapping[SolarDeviceName, Mapping[SolarOutputName, OutputData]]:
        """Map model outputs to solar-specific output names."""
        connection = model_outputs[f"{name}:connection"]

        solar_outputs: dict[SolarOutputName, OutputData] = {
            SOLAR_POWER: replace(connection[CONNECTION_POWER_SOURCE_TARGET], type=OUTPUT_TYPE_POWER),
            SOLAR_FORECAST_LIMIT: connection[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET],
        }

        return {SOLAR_DEVICE_SOLAR: solar_outputs}


adapter = SolarAdapter()
