"""Connection element schema definitions."""

from typing import Any, Final, Literal, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.sections import (
    SECTION_ADVANCED,
    SECTION_BASIC,
    SECTION_LIMITS,
    SECTION_PRICING,
    BasicNameConfig,
    BasicNameData,
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


class ConnectionLimitsConfig(TypedDict, total=False):
    """Optional source/target power limits configuration."""

    max_power_source_target: str | float
    max_power_target_source: str | float


class ConnectionLimitsData(TypedDict, total=False):
    """Loaded source/target power limits."""

    max_power_source_target: NDArray[np.floating[Any]] | float
    max_power_target_source: NDArray[np.floating[Any]] | float


class ConnectionPricingConfig(TypedDict, total=False):
    """Optional directional pricing configuration."""

    price_source_target: str | float
    price_target_source: str | float


class ConnectionPricingData(TypedDict, total=False):
    """Loaded directional pricing values."""

    price_source_target: NDArray[np.floating[Any]] | float
    price_target_source: NDArray[np.floating[Any]] | float


class ConnectionAdvancedConfig(TypedDict, total=False):
    """Optional source/target efficiency configuration."""

    efficiency_source_target: str | float
    efficiency_target_source: str | float


class ConnectionAdvancedData(TypedDict, total=False):
    """Loaded source/target efficiency values."""

    efficiency_source_target: NDArray[np.floating[Any]] | float
    efficiency_target_source: NDArray[np.floating[Any]] | float


class ConnectionConfigSchema(TypedDict):
    """Connection element configuration as stored in Home Assistant."""

    element_type: Literal["connection"]
    basic: BasicNameConfig
    endpoints: EndpointsConfig
    limits: ConnectionLimitsConfig
    pricing: ConnectionPricingConfig
    advanced: ConnectionAdvancedConfig


class ConnectionConfigData(TypedDict):
    """Connection element configuration with loaded values."""

    element_type: Literal["connection"]
    basic: BasicNameData
    endpoints: EndpointsData
    limits: ConnectionLimitsData
    pricing: ConnectionPricingData
    advanced: ConnectionAdvancedData


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
    "SECTION_BASIC",
    "SECTION_ENDPOINTS",
    "SECTION_LIMITS",
    "SECTION_PRICING",
    "ConnectionConfigData",
    "ConnectionConfigSchema",
]
