"""Solar element schema definitions."""

from typing import Final, Literal, TypedDict

from custom_components.haeo.schema.elements import ElementType
from custom_components.haeo.sections import (
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_SOURCE_TARGET,
    SECTION_COMMON,
    SECTION_CURTAILMENT,
    SECTION_FORECAST,
    SECTION_PRICING,
    ConnectedCommonConfig,
    ConnectedCommonData,
    CurtailmentConfig,
    CurtailmentData,
    ForecastConfig,
    ForecastData,
    PricingConfig,
    PricingData,
)

ELEMENT_TYPE = ElementType.SOLAR

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_CURTAILMENT, CONF_PRICE_SOURCE_TARGET})


class SolarConfigSchema(TypedDict):
    """Solar element configuration as stored in Home Assistant.

    Schema mode contains entity IDs and constant values from the config flow.
    """

    element_type: Literal[ElementType.SOLAR]
    common: ConnectedCommonConfig
    forecast: ForecastConfig
    pricing: PricingConfig
    curtailment: CurtailmentConfig


class SolarConfigData(TypedDict):
    """Solar element configuration with loaded values."""

    element_type: Literal[ElementType.SOLAR]
    common: ConnectedCommonData
    forecast: ForecastData
    pricing: PricingData
    curtailment: CurtailmentData


__all__ = [
    "CONF_CURTAILMENT",
    "CONF_FORECAST",
    "CONF_PRICE_SOURCE_TARGET",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_COMMON",
    "SECTION_CURTAILMENT",
    "SECTION_FORECAST",
    "SECTION_PRICING",
    "SolarConfigData",
    "SolarConfigSchema",
]
