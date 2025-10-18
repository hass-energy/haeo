"""Forecast load element configuration for HAEO integration."""

from typing import Any, Final, Literal, TypedDict

from custom_components.haeo.schema.fields import (
    NameFieldData,
    NameFieldSchema,
    PowerForecastsFieldData,
    PowerForecastsFieldSchema,
)

ELEMENT_TYPE: Final = "forecast_load"

CONF_FORECAST: Final = "forecast"


class ForecastLoadConfigSchema(TypedDict):
    """Forecast load element configuration."""

    element_type: Literal["forecast_load"]
    name: NameFieldSchema
    forecast: PowerForecastsFieldSchema


class ForecastLoadConfigData(TypedDict):
    """Forecast load element configuration."""

    element_type: Literal["forecast_load"]
    name: NameFieldData
    forecast: PowerForecastsFieldData


FORECAST_LOAD_CONFIG_DEFAULTS: dict[str, Any] = {}


def model_description(config: ForecastLoadConfigData) -> str:
    """Generate model description string for forecast load element.

    Args:
        config: Forecast load configuration data.

    Returns:
        Formatted model description string.

    """
    return f"Forecast load: {config['name']}"
