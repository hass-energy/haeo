"""Connection element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.core import HomeAssistant

from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.model import OUTPUT_TYPE_POWER_FLOW, ModelOutputName
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.power_connection import (
    CONNECTION_POWER_ACTIVE,
    CONNECTION_POWER_MAX_SOURCE_TARGET,
    CONNECTION_POWER_MAX_TARGET_SOURCE,
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_PRICE_SOURCE_TARGET,
    CONNECTION_PRICE_TARGET_SOURCE,
    CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
    CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
    CONNECTION_TIME_SLICE,
    POWER_CONNECTION_OUTPUT_NAMES,
    PowerConnectionOutputName,
)

from .flow import ConnectionSubentryFlowHandler
from .schema import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    CONF_SOURCE,
    CONF_TARGET,
    ELEMENT_TYPE,
    ConnectionConfigData,
    ConnectionConfigSchema,
)

# Re-export power connection output names
CONNECTION_OUTPUT_NAMES: Final[frozenset[PowerConnectionOutputName]] = POWER_CONNECTION_OUTPUT_NAMES

type ConnectionDeviceName = Literal["connection"]

CONNECTION_DEVICE_NAMES: Final[frozenset[ConnectionDeviceName]] = frozenset(
    (CONNECTION_DEVICE_CONNECTION := "connection",),
)


class ConnectionAdapter:
    """Adapter for Connection elements."""

    element_type: str = ELEMENT_TYPE
    flow_class: type = ConnectionSubentryFlowHandler
    advanced: bool = True
    connectivity: str = "never"

    def available(self, config: ConnectionConfigSchema, *, hass: HomeAssistant, **_kwargs: Any) -> bool:
        """Check if connection configuration can be loaded."""
        ts_loader = TimeSeriesLoader()

        # Check all optional time series fields if present
        optional_fields = [
            CONF_MAX_POWER_SOURCE_TARGET,
            CONF_MAX_POWER_TARGET_SOURCE,
            CONF_EFFICIENCY_SOURCE_TARGET,
            CONF_EFFICIENCY_TARGET_SOURCE,
            CONF_PRICE_SOURCE_TARGET,
            CONF_PRICE_TARGET_SOURCE,
        ]

        for field in optional_fields:
            if field in config and not ts_loader.available(hass=hass, value=config[field]):
                return False

        return True

    async def load(
        self,
        config: ConnectionConfigSchema,
        *,
        hass: HomeAssistant,
        forecast_times: Sequence[float],
    ) -> ConnectionConfigData:
        """Load connection configuration values from sensors."""
        ts_loader = TimeSeriesLoader()

        data: ConnectionConfigData = {
            "element_type": config["element_type"],
            "name": config["name"],
            "source": config[CONF_SOURCE],
            "target": config[CONF_TARGET],
        }

        # Load optional time series fields
        if CONF_MAX_POWER_SOURCE_TARGET in config:
            data["max_power_source_target"] = await ts_loader.load(
                hass=hass, value=config[CONF_MAX_POWER_SOURCE_TARGET], forecast_times=forecast_times
            )
        if CONF_MAX_POWER_TARGET_SOURCE in config:
            data["max_power_target_source"] = await ts_loader.load(
                hass=hass, value=config[CONF_MAX_POWER_TARGET_SOURCE], forecast_times=forecast_times
            )
        if CONF_EFFICIENCY_SOURCE_TARGET in config:
            data["efficiency_source_target"] = await ts_loader.load(
                hass=hass, value=config[CONF_EFFICIENCY_SOURCE_TARGET], forecast_times=forecast_times
            )
        if CONF_EFFICIENCY_TARGET_SOURCE in config:
            data["efficiency_target_source"] = await ts_loader.load(
                hass=hass, value=config[CONF_EFFICIENCY_TARGET_SOURCE], forecast_times=forecast_times
            )
        if CONF_PRICE_SOURCE_TARGET in config:
            data["price_source_target"] = await ts_loader.load(
                hass=hass, value=config[CONF_PRICE_SOURCE_TARGET], forecast_times=forecast_times
            )
        if CONF_PRICE_TARGET_SOURCE in config:
            data["price_target_source"] = await ts_loader.load(
                hass=hass, value=config[CONF_PRICE_TARGET_SOURCE], forecast_times=forecast_times
            )

        return data

    def create_model_elements(self, config: ConnectionConfigData) -> list[dict[str, Any]]:
        """Create model elements for Connection configuration."""
        return [
            {
                "element_type": "connection",
                "name": config["name"],
                "source": config["source"],
                "target": config["target"],
                "max_power_source_target": config.get("max_power_source_target"),
                "max_power_target_source": config.get("max_power_target_source"),
                "efficiency_source_target": config.get("efficiency_source_target"),
                "efficiency_target_source": config.get("efficiency_target_source"),
                "price_source_target": config.get("price_source_target"),
                "price_target_source": config.get("price_target_source"),
            }
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]],
        _config: ConnectionConfigData,
    ) -> Mapping[ConnectionDeviceName, Mapping[PowerConnectionOutputName, OutputData]]:
        """Map model outputs to connection-specific output names."""
        connection = model_outputs[name]

        connection_outputs: dict[PowerConnectionOutputName, OutputData] = {
            CONNECTION_POWER_SOURCE_TARGET: connection[CONNECTION_POWER_SOURCE_TARGET],
            CONNECTION_POWER_TARGET_SOURCE: connection[CONNECTION_POWER_TARGET_SOURCE],
        }

        # Active connection power (source_target - target_source)
        connection_outputs[CONNECTION_POWER_ACTIVE] = replace(
            connection[CONNECTION_POWER_SOURCE_TARGET],
            values=[
                st - ts
                for st, ts in zip(
                    connection[CONNECTION_POWER_SOURCE_TARGET].values,
                    connection[CONNECTION_POWER_TARGET_SOURCE].values,
                    strict=True,
                )
            ],
            direction=None,
            type=OUTPUT_TYPE_POWER_FLOW,
        )

        # Optional outputs (only present if configured)
        if CONNECTION_POWER_MAX_SOURCE_TARGET in connection:
            connection_outputs[CONNECTION_POWER_MAX_SOURCE_TARGET] = connection[CONNECTION_POWER_MAX_SOURCE_TARGET]
            connection_outputs[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET] = connection[
                CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET
            ]

        if CONNECTION_POWER_MAX_TARGET_SOURCE in connection:
            connection_outputs[CONNECTION_POWER_MAX_TARGET_SOURCE] = connection[CONNECTION_POWER_MAX_TARGET_SOURCE]
            connection_outputs[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE] = connection[
                CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE
            ]

        if CONNECTION_PRICE_SOURCE_TARGET in connection:
            connection_outputs[CONNECTION_PRICE_SOURCE_TARGET] = connection[CONNECTION_PRICE_SOURCE_TARGET]

        if CONNECTION_PRICE_TARGET_SOURCE in connection:
            connection_outputs[CONNECTION_PRICE_TARGET_SOURCE] = connection[CONNECTION_PRICE_TARGET_SOURCE]

        if CONNECTION_TIME_SLICE in connection:
            connection_outputs[CONNECTION_TIME_SLICE] = connection[CONNECTION_TIME_SLICE]

        return {CONNECTION_DEVICE_CONNECTION: connection_outputs}


adapter = ConnectionAdapter()
