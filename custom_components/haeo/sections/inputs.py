"""Shared definitions for input configuration sections."""

from typing import Any, Final, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.flows.field_schema import SectionDefinition

SECTION_INPUTS: Final = "inputs"
CONF_FORECAST: Final = "forecast"


class ForecastInputsConfig(TypedDict):
    """Input configuration for forecast values."""

    forecast: list[str] | str | float


class ForecastInputsData(TypedDict):
    """Loaded forecast values for inputs."""

    forecast: NDArray[np.floating[Any]] | float


def inputs_section(fields: tuple[str, ...] = (CONF_FORECAST,), *, collapsed: bool = False) -> SectionDefinition:
    """Return the standard inputs section definition."""
    return SectionDefinition(key=SECTION_INPUTS, fields=fields, collapsed=collapsed)


__all__ = [  # noqa: RUF022
    "CONF_FORECAST",
    "ForecastInputsConfig",
    "ForecastInputsData",
    "inputs_section",
    "SECTION_INPUTS",
]
