"""Load element schema definitions."""

from typing import Final, Literal, TypedDict

from custom_components.haeo.sections import (
    CONF_FORECAST,
    SECTION_COMMON,
    SECTION_FORECAST,
    ConnectedCommonConfig,
    ConnectedCommonData,
    ForecastConfig,
    ForecastData,
)

ELEMENT_TYPE: Final = "load"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset()


class LoadConfigSchema(TypedDict):
    """Load element configuration as stored in Home Assistant."""

    element_type: Literal["load"]
    common: ConnectedCommonConfig
    forecast: ForecastConfig


class LoadConfigData(TypedDict):
    """Load element configuration with loaded values."""

    element_type: Literal["load"]
    common: ConnectedCommonData
    forecast: ForecastData


__all__ = [
    "CONF_FORECAST",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_COMMON",
    "SECTION_FORECAST",
    "LoadConfigData",
    "LoadConfigSchema",
]
