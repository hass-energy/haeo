"""Load element schema definitions."""

from typing import Final, Literal, TypedDict

from custom_components.haeo.sections import (
    CONF_FORECAST,
    SECTION_BASIC,
    SECTION_INPUTS,
    BasicNameConnectionConfig,
    BasicNameConnectionData,
    ForecastInputsConfig,
    ForecastInputsData,
)

ELEMENT_TYPE: Final = "load"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset()


class LoadConfigSchema(TypedDict):
    """Load element configuration as stored in Home Assistant."""

    element_type: Literal["load"]
    basic: BasicNameConnectionConfig
    inputs: ForecastInputsConfig


class LoadConfigData(TypedDict):
    """Load element configuration with loaded values."""

    element_type: Literal["load"]
    basic: BasicNameConnectionData
    inputs: ForecastInputsData


__all__ = [
    "CONF_FORECAST",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_BASIC",
    "SECTION_INPUTS",
    "LoadConfigData",
    "LoadConfigSchema",
]
