"""Forecast load element configuration for HAEO integration."""

from dataclasses import dataclass
from typing import Literal

from custom_components.haeo.schema.fields import NameField, PowerForecastsField


@dataclass
class ForecastLoadConfig:
    """Forecast load element configuration."""

    name: NameField

    forecast: PowerForecastsField

    element_type: Literal["forecast_load"] = "forecast_load"
