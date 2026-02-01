"""Solar element schema definitions."""

from typing import Final, Literal, TypedDict

from custom_components.haeo.sections import (
    CONF_FORECAST,
    SECTION_ADVANCED,
    SECTION_DETAILS,
    SECTION_FORECAST,
    SECTION_PRICING,
    AdvancedConfig,
    AdvancedData,
    DetailsConfig,
    DetailsData,
    ForecastConfig,
    ForecastData,
    PricingConfig,
    PricingData,
)

ELEMENT_TYPE: Final = "solar"

CONF_CURTAILMENT: Final = "curtailment"
CONF_PRICE_PRODUCTION: Final = "price_production"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_CURTAILMENT, CONF_PRICE_PRODUCTION})


class SolarConfigSchema(TypedDict):
    """Solar element configuration as stored in Home Assistant.

    Schema mode contains entity IDs and constant values from the config flow.
    """

    element_type: Literal["solar"]
    basic: DetailsConfig
    inputs: ForecastConfig
    pricing: PricingConfig
    advanced: AdvancedConfig


class SolarConfigData(TypedDict):
    """Solar element configuration with loaded values."""

    element_type: Literal["solar"]
    basic: DetailsData
    inputs: ForecastData
    pricing: PricingData
    advanced: AdvancedData


__all__ = [
    "CONF_CURTAILMENT",
    "CONF_FORECAST",
    "CONF_PRICE_PRODUCTION",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_ADVANCED",
    "SECTION_DETAILS",
    "SECTION_FORECAST",
    "SECTION_PRICING",
    "SolarAdvancedConfig",
    "SolarConfigData",
    "SolarConfigSchema",
    "SolarPricingConfig",
]
