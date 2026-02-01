"""Shared definitions for forecast configuration sections."""

from typing import Any, Final, TypedDict

import numpy as np
from numpy.typing import NDArray
import voluptuous as vol

from custom_components.haeo.flows.field_schema import SectionDefinition

SECTION_FORECAST: Final = "forecast"
CONF_FORECAST: Final = "forecast"


class ForecastConfig(TypedDict):
    """Forecast configuration for input values."""

    forecast: list[str] | str | float


class ForecastData(TypedDict):
    """Loaded forecast values for inputs."""

    forecast: NDArray[np.floating[Any]] | float


def forecast_section(fields: tuple[str, ...] = (CONF_FORECAST,), *, collapsed: bool = False) -> SectionDefinition:
    """Return the standard forecast section definition."""
    return SectionDefinition(key=SECTION_FORECAST, fields=fields, collapsed=collapsed)


def build_forecast_fields() -> dict[str, tuple[vol.Marker, Any]]:
    """Build forecast field entries for config flows."""
    return {}


__all__ = [  # noqa: RUF022
    "CONF_FORECAST",
    "ForecastConfig",
    "ForecastData",
    "SECTION_FORECAST",
    "build_forecast_fields",
    "forecast_section",
]
