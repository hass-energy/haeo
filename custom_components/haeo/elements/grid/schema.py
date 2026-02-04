"""Grid element schema definitions."""

from typing import Final, Literal, TypedDict

from custom_components.haeo.sections import (
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
    ConnectedCommonConfig,
    ConnectedCommonData,
    PowerLimitsConfig,
    PowerLimitsData,
)
from custom_components.haeo.sections.pricing import PricingValueConfig, PricingValueData

ELEMENT_TYPE: Final = "grid"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        CONF_MAX_POWER_SOURCE_TARGET,
        CONF_MAX_POWER_TARGET_SOURCE,
    }
)


class GridPricingConfig(TypedDict):
    """Directional pricing configuration with required values."""

    price_source_target: PricingValueConfig
    price_target_source: PricingValueConfig


class GridPricingData(TypedDict):
    """Loaded directional pricing values with required entries."""

    price_source_target: PricingValueData
    price_target_source: PricingValueData


class GridConfigSchema(TypedDict):
    """Grid element configuration as stored in Home Assistant."""

    element_type: Literal["grid"]
    common: ConnectedCommonConfig
    pricing: GridPricingConfig
    power_limits: PowerLimitsConfig


class GridConfigData(TypedDict):
    """Grid element configuration with loaded values."""

    element_type: Literal["grid"]
    common: ConnectedCommonData
    pricing: GridPricingData
    power_limits: PowerLimitsData


__all__ = [
    "CONF_MAX_POWER_SOURCE_TARGET",
    "CONF_MAX_POWER_TARGET_SOURCE",
    "CONF_PRICE_SOURCE_TARGET",
    "CONF_PRICE_TARGET_SOURCE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_COMMON",
    "SECTION_POWER_LIMITS",
    "SECTION_PRICING",
    "GridConfigData",
    "GridConfigSchema",
]
