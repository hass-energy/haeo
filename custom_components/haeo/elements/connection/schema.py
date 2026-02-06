"""Connection element schema definitions."""

from typing import Final, Literal, TypedDict

from custom_components.haeo.schema import ConnectionTarget
from custom_components.haeo.sections import (
    CONF_DEMAND_BLOCK_HOURS,
    CONF_DEMAND_CURRENT_ENERGY_SOURCE_TARGET,
    CONF_DEMAND_CURRENT_ENERGY_TARGET_SOURCE,
    CONF_DEMAND_DAYS,
    CONF_DEMAND_PRICE_SOURCE_TARGET,
    CONF_DEMAND_PRICE_TARGET_SOURCE,
    CONF_DEMAND_WINDOW_SOURCE_TARGET,
    CONF_DEMAND_WINDOW_TARGET_SOURCE,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
    CommonConfig,
    CommonData,
    EfficiencyConfig,
    EfficiencyData,
    PowerLimitsConfig,
    PowerLimitsData,
    PricingConfig,
    PricingData,
)

ELEMENT_TYPE: Final = "connection"

SECTION_ENDPOINTS: Final = "endpoints"

CONF_SOURCE: Final = "source"
CONF_TARGET: Final = "target"
OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        CONF_MAX_POWER_SOURCE_TARGET,
        CONF_MAX_POWER_TARGET_SOURCE,
        CONF_EFFICIENCY_SOURCE_TARGET,
        CONF_EFFICIENCY_TARGET_SOURCE,
        CONF_PRICE_SOURCE_TARGET,
        CONF_PRICE_TARGET_SOURCE,
        CONF_DEMAND_WINDOW_SOURCE_TARGET,
        CONF_DEMAND_WINDOW_TARGET_SOURCE,
        CONF_DEMAND_PRICE_SOURCE_TARGET,
        CONF_DEMAND_PRICE_TARGET_SOURCE,
        CONF_DEMAND_CURRENT_ENERGY_SOURCE_TARGET,
        CONF_DEMAND_CURRENT_ENERGY_TARGET_SOURCE,
        CONF_DEMAND_BLOCK_HOURS,
        CONF_DEMAND_DAYS,
    }
)


class EndpointsConfig(TypedDict):
    """Endpoint configuration for source/target pairs."""

    source: ConnectionTarget
    target: ConnectionTarget


class EndpointsData(TypedDict):
    """Loaded endpoint values."""

    source: ConnectionTarget
    target: ConnectionTarget


class ConnectionConfigSchema(TypedDict):
    """Connection element configuration as stored in Home Assistant."""

    element_type: Literal["connection"]
    common: CommonConfig
    endpoints: EndpointsConfig
    power_limits: PowerLimitsConfig
    pricing: PricingConfig
    efficiency: EfficiencyConfig


class ConnectionConfigData(TypedDict):
    """Connection element configuration with loaded values."""

    element_type: Literal["connection"]
    common: CommonData
    endpoints: EndpointsData
    power_limits: PowerLimitsData
    pricing: PricingData
    efficiency: EfficiencyData
__all__ = [
    "CONF_DEMAND_BLOCK_HOURS",
    "CONF_DEMAND_CURRENT_ENERGY_SOURCE_TARGET",
    "CONF_DEMAND_CURRENT_ENERGY_TARGET_SOURCE",
    "CONF_DEMAND_DAYS",
    "CONF_DEMAND_PRICE_SOURCE_TARGET",
    "CONF_DEMAND_PRICE_TARGET_SOURCE",
    "CONF_DEMAND_WINDOW_SOURCE_TARGET",
    "CONF_DEMAND_WINDOW_TARGET_SOURCE",
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
    "SECTION_COMMON",
    "SECTION_EFFICIENCY",
    "SECTION_ENDPOINTS",
    "SECTION_POWER_LIMITS",
    "SECTION_PRICING",
    "ConnectionConfigData",
    "ConnectionConfigSchema",
]
