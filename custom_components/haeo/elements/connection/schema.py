"""Connection element schema definitions."""

from typing import Final, Literal, TypedDict

from custom_components.haeo.sections import (
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_ADVANCED,
    SECTION_COMMON,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
    AdvancedConfig,
    AdvancedData,
    CommonConfig,
    CommonData,
    PowerLimitsConfig,
    PowerLimitsData,
    PricingConfig,
    PricingData,
)

ELEMENT_TYPE: Final = "connection"

SECTION_ENDPOINTS: Final = "endpoints"

CONF_SOURCE: Final = "source"
CONF_TARGET: Final = "target"

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
    common: CommonConfig
    endpoints: EndpointsConfig
    power_limits: PowerLimitsConfig
    pricing: PricingConfig
    advanced: AdvancedConfig


class ConnectionConfigData(TypedDict):
    """Connection element configuration with loaded values."""

    element_type: Literal["connection"]
    common: CommonData
    endpoints: EndpointsData
    power_limits: PowerLimitsData
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
    "SECTION_COMMON",
    "SECTION_ENDPOINTS",
    "SECTION_POWER_LIMITS",
    "SECTION_PRICING",
    "ConnectionConfigData",
    "ConnectionConfigSchema",
]
