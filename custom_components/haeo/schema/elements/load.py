"""Load element schema definitions."""

from typing import Final, Literal, TypedDict

from custom_components.haeo.schema.elements import ElementType
from custom_components.haeo.sections import (
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_TARGET_SOURCE,
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

ELEMENT_TYPE = ElementType.LOAD

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_CURTAILMENT, CONF_PRICE_TARGET_SOURCE})


class LoadConfigSchema(TypedDict):
    """Load element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.LOAD]
    common: ConnectedCommonConfig
    forecast: ForecastConfig
    pricing: PricingConfig
    curtailment: CurtailmentConfig


class LoadConfigData(TypedDict):
    """Load element configuration with loaded values."""

    element_type: Literal[ElementType.LOAD]
    common: ConnectedCommonData
    forecast: ForecastData
    pricing: PricingData
    curtailment: CurtailmentData


__all__ = [
    "CONF_CURTAILMENT",
    "CONF_FORECAST",
    "CONF_PRICE_TARGET_SOURCE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_COMMON",
    "SECTION_CURTAILMENT",
    "SECTION_FORECAST",
    "SECTION_PRICING",
    "LoadConfigData",
    "LoadConfigSchema",
]
