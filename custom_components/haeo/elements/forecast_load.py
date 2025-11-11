"""Forecast load element configuration for HAEO integration."""

from typing import Any, Final, Literal, TypedDict

from custom_components.haeo.schema.fields import (
    NameFieldData,
    NameFieldSchema,
    PowerSensorsFieldData,
    PowerSensorsFieldSchema,
)

ELEMENT_TYPE: Final = "forecast_load"

CONF_FORECAST: Final = "forecast"


class ForecastLoadConfigSchema(TypedDict):
    """Forecast load element configuration."""

    element_type: Literal["forecast_load"]
    name: NameFieldSchema
    forecast: PowerSensorsFieldSchema


class ForecastLoadConfigData(TypedDict):
    """Forecast load element configuration."""

    element_type: Literal["forecast_load"]
    name: NameFieldData
    forecast: PowerSensorsFieldData


CONFIG_DEFAULTS: dict[str, Any] = {}
