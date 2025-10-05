"""Forecast load element configuration for HAEO integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .fields import NameField, PowerForecastField


@dataclass
class ForecastLoadConfig:
    """Forecast load element configuration."""

    name: NameField

    forecast: PowerForecastField

    element_type: Literal["forecast_load"] = "forecast_load"
