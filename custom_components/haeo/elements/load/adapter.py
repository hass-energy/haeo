"""Load element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.core import HomeAssistant

from custom_components.haeo.data.loader import ConstantLoader, TimeSeriesLoader
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.const import OUTPUT_TYPE_POWER
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.power_connection import (
    CONNECTION_POWER_MAX_TARGET_SOURCE,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_PRICE_TARGET_SOURCE,
    CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
)

from .flow import LoadSubentryFlowHandler
from .schema import (
    CONF_CONNECTION,
    CONF_FORECAST,
    CONF_SHEDDABLE,
    CONF_VALUE_RUNNING,
    DEFAULTS,
    ELEMENT_TYPE,
    LoadConfigData,
    LoadConfigSchema,
)

# Load output names
type LoadOutputName = Literal[
    "load_power",
    "load_power_possible",
    "load_value",
    "load_forecast_limit_price",
]

LOAD_OUTPUT_NAMES: Final[frozenset[LoadOutputName]] = frozenset(
    (
        LOAD_POWER := "load_power",
        LOAD_POWER_POSSIBLE := "load_power_possible",
        LOAD_VALUE := "load_value",
        # Shadow prices
        LOAD_FORECAST_LIMIT_PRICE := "load_forecast_limit_price",
    )
)

type LoadDeviceName = Literal["load"]

LOAD_DEVICE_NAMES: Final[frozenset[LoadDeviceName]] = frozenset(
    (LOAD_DEVICE_LOAD := "load",),
)


class LoadAdapter:
    """Adapter for Load elements."""

    element_type: str = ELEMENT_TYPE
    flow_class: type = LoadSubentryFlowHandler
    advanced: bool = False
    connectivity: str = "always"

    def available(self, config: LoadConfigSchema, *, hass: HomeAssistant, **_kwargs: Any) -> bool:
        """Check if load configuration can be loaded."""
        ts_loader = TimeSeriesLoader()
        return ts_loader.available(hass=hass, value=config[CONF_FORECAST])

    async def load(
        self,
        config: LoadConfigSchema,
        *,
        hass: HomeAssistant,
        forecast_times: Sequence[float],
    ) -> LoadConfigData:
        """Load load configuration values from sensors."""
        ts_loader = TimeSeriesLoader()
        const_loader_float = ConstantLoader[float](float)
        const_loader_bool = ConstantLoader[bool](bool)

        forecast = await ts_loader.load(
            hass=hass,
            value=config[CONF_FORECAST],
            forecast_times=forecast_times,
        )

        data: LoadConfigData = {
            "element_type": config["element_type"],
            "name": config["name"],
            "connection": config[CONF_CONNECTION],
            "forecast": forecast,
        }

        # Load optional fields
        if CONF_SHEDDABLE in config:
            data["sheddable"] = await const_loader_bool.load(value=config[CONF_SHEDDABLE])
        if CONF_VALUE_RUNNING in config:
            data["value_running"] = await const_loader_float.load(value=config[CONF_VALUE_RUNNING])

        return data

    def create_model_elements(self, config: LoadConfigData) -> list[dict[str, Any]]:
        """Create model elements for Load configuration."""
        connection_params: dict[str, Any] = {
            "element_type": "connection",
            "name": f"{config['name']}:connection",
            "source": config["name"],
            "target": config["connection"],
            "max_power_source_target": 0.0,
            "max_power_target_source": config["forecast"],
            "fixed_power": not config.get("sheddable", DEFAULTS[CONF_SHEDDABLE]),
        }

        # Only include price_target_source if value_running is specified
        if (value_running := config.get("value_running")) is not None:
            connection_params["price_target_source"] = value_running

        return [
            # Create Node for the load (sink only - consumes power)
            {"element_type": "node", "name": config["name"], "is_source": False, "is_sink": True},
            # Create Connection from node to load (power flows TO the load)
            connection_params,
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]],
        _config: LoadConfigData,
    ) -> Mapping[LoadDeviceName, Mapping[LoadOutputName, OutputData]]:
        """Map model outputs to load-specific output names."""
        connection = model_outputs[f"{name}:connection"]

        load_outputs: dict[LoadOutputName, OutputData] = {
            LOAD_POWER: replace(connection[CONNECTION_POWER_TARGET_SOURCE], type=OUTPUT_TYPE_POWER),
            LOAD_POWER_POSSIBLE: connection[CONNECTION_POWER_MAX_TARGET_SOURCE],
            # Only the max limit has meaning, the source sink power balance is always zero
            LOAD_FORECAST_LIMIT_PRICE: connection[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE],
        }

        if CONNECTION_PRICE_TARGET_SOURCE in connection:
            load_outputs[LOAD_VALUE] = connection[CONNECTION_PRICE_TARGET_SOURCE]

        return {LOAD_DEVICE_LOAD: load_outputs}


adapter = LoadAdapter()
