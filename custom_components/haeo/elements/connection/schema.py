"""Connection element schema definitions."""

from typing import Final, Literal, TypedDict

from custom_components.haeo.sections import (
    SECTION_ADVANCED,
    SECTION_DETAILS,
    SECTION_LIMITS,
    SECTION_PRICING,
    AdvancedConfig,
    AdvancedData,
    DetailsConfig,
    DetailsData,
    LimitsConfig,
    LimitsData,
    PricingConfig,
    PricingData,
)

ELEMENT_TYPE: Final = "connection"

SECTION_ENDPOINTS: Final = "endpoints"

CONF_SOURCE: Final = "source"
CONF_TARGET: Final = "target"

CONF_MAX_POWER_SOURCE_TARGET: Final = "max_power_source_target"
CONF_MAX_POWER_TARGET_SOURCE: Final = "max_power_target_source"

CONF_PRICE_SOURCE_TARGET: Final = "price_source_target"
CONF_PRICE_TARGET_SOURCE: Final = "price_target_source"

CONF_EFFICIENCY_SOURCE_TARGET: Final = "efficiency_source_target"
CONF_EFFICIENCY_TARGET_SOURCE: Final = "efficiency_target_source"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        CONF_MAX_POWER_SOURCE_TARGET,
        CONF_MAX_POWER_TARGET_SOURCE,
        CONF_EFFICIENCY_SOURCE_TARGET,
        CONF_EFFICIENCY_TARGET_SOURCE,
        CONF_PRICE_SOURCE_TARGET,
        CONF_PRICE_TARGET_SOURCE,
    }
)


class EndpointsConfig(TypedDict):
    """Endpoint configuration for source/target pairs."""

    source: str
    target: str


class EndpointsData(TypedDict):
    """Loaded endpoint values."""

    source: str
    target: str


class ConnectionConfigSchema(TypedDict):
    """Connection element configuration as stored in Home Assistant."""

    element_type: Literal["connection"]
    basic: DetailsConfig
    endpoints: EndpointsConfig
    limits: LimitsConfig
    pricing: PricingConfig
    advanced: AdvancedConfig


class ConnectionConfigData(TypedDict):
    """Connection element configuration with loaded values."""

    element_type: Literal["connection"]
    basic: DetailsData
    endpoints: EndpointsData
    limits: LimitsData
    pricing: PricingData
    advanced: AdvancedData


__all__ = [
    "CONF_EFFICIENCY_SOURCE_TARGET",
    "CONF_EFFICIENCY_TARGET_SOURCE",
    "CONF_MAX_POWER_SOURCE_TARGET",
    "CONF_MAX_POWER_TARGET_SOURCE",
    "CONF_PRICE_SOURCE_TARGET",
    "CONF_PRICE_TARGET_SOURCE",
    "CONF_SOURCE",
    "CONF_TARGET",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_ADVANCED",
    "SECTION_DETAILS",
    "SECTION_ENDPOINTS",
    "SECTION_LIMITS",
    "SECTION_PRICING",
    "ConnectionConfigData",
    "ConnectionConfigSchema",
]
