"""Connection element schema definitions."""

from typing import Final, Literal, NotRequired, TypedDict

from custom_components.haeo.schema import ConnectionTarget
from custom_components.haeo.sections import (
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
SECTION_SEGMENT_ORDER: Final = "segment_order"

CONF_SOURCE: Final = "source"
CONF_TARGET: Final = "target"
CONF_MIRROR_SEGMENT_ORDER: Final = "mirror_segment_order"

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

    source: ConnectionTarget
    target: ConnectionTarget


class EndpointsData(TypedDict):
    """Loaded endpoint values."""

    source: ConnectionTarget
    target: ConnectionTarget


class SegmentOrderConfig(TypedDict, total=False):
    """Segment order configuration values."""

    mirror_segment_order: bool


class SegmentOrderData(TypedDict, total=False):
    """Loaded segment order values."""

    mirror_segment_order: bool


class ConnectionConfigSchema(TypedDict):
    """Connection element configuration as stored in Home Assistant."""

    element_type: Literal["connection"]
    common: CommonConfig
    endpoints: EndpointsConfig
    segment_order: NotRequired[SegmentOrderConfig]
    power_limits: PowerLimitsConfig
    pricing: PricingConfig
    efficiency: EfficiencyConfig


class ConnectionConfigData(TypedDict):
    """Connection element configuration with loaded values."""

    element_type: Literal["connection"]
    common: CommonData
    endpoints: EndpointsData
    segment_order: NotRequired[SegmentOrderData]
    power_limits: PowerLimitsData
    pricing: PricingData
    efficiency: EfficiencyData


__all__ = [
    "CONF_EFFICIENCY_SOURCE_TARGET",
    "CONF_EFFICIENCY_TARGET_SOURCE",
    "CONF_MAX_POWER_SOURCE_TARGET",
    "CONF_MAX_POWER_TARGET_SOURCE",
    "CONF_MIRROR_SEGMENT_ORDER",
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
    "SECTION_SEGMENT_ORDER",
    "ConnectionConfigData",
    "ConnectionConfigSchema",
    "SegmentOrderConfig",
    "SegmentOrderData",
]
