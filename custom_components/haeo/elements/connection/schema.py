"""Connection element schema definitions."""

from typing import Any, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

ELEMENT_TYPE: Final = "connection"

# Configuration field names
CONF_SOURCE: Final = "source"
CONF_TARGET: Final = "target"
CONF_MAX_POWER_SOURCE_TARGET: Final = "max_power_source_target"
CONF_MAX_POWER_TARGET_SOURCE: Final = "max_power_target_source"
CONF_EFFICIENCY_SOURCE_TARGET: Final = "efficiency_source_target"
CONF_EFFICIENCY_TARGET_SOURCE: Final = "efficiency_target_source"
CONF_PRICE_SOURCE_TARGET: Final = "price_source_target"
CONF_PRICE_TARGET_SOURCE: Final = "price_target_source"
CONF_SECTION_BASIC: Final = "basic"
CONF_SECTION_LIMITS: Final = "limits"
CONF_SECTION_ADVANCED: Final = "advanced"

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


class ConnectionBasicConfig(TypedDict):
    """Basic configuration for connection elements."""

    name: str
    source: str  # Source element name
    target: str  # Target element name


class ConnectionLimitsConfig(TypedDict, total=False):
    """Limit configuration for connection elements."""

    max_power_source_target: str | float  # Entity ID or constant kW
    max_power_target_source: str | float  # Entity ID or constant kW


class ConnectionAdvancedConfig(TypedDict, total=False):
    """Advanced configuration for connection elements."""

    efficiency_source_target: str | float  # Entity ID or constant %
    efficiency_target_source: str | float  # Entity ID or constant %
    price_source_target: str | float  # Entity ID or constant $/kWh
    price_target_source: str | float  # Entity ID or constant $/kWh


class ConnectionConfigSchema(TypedDict):
    """Connection element configuration as stored in Home Assistant.

    Schema mode contains entity IDs and constant values from the config flow.
    Values can be:
    - str: Entity ID when linking to a sensor
    - float: Constant value when using HAEO Configurable
    - NotRequired: Field not present when using default
    """

    element_type: Literal["connection"]
    basic: ConnectionBasicConfig
    limits: ConnectionLimitsConfig
    advanced: ConnectionAdvancedConfig


class ConnectionBasicData(TypedDict):
    """Loaded basic values for connection elements."""

    name: str
    source: str  # Source element name
    target: str  # Target element name


class ConnectionLimitsData(TypedDict, total=False):
    """Loaded limit values for connection elements."""

    max_power_source_target: NotRequired[NDArray[np.floating[Any]] | float]  # Loaded power limit per period (kW)
    max_power_target_source: NotRequired[NDArray[np.floating[Any]] | float]  # Loaded power limit per period (kW)


class ConnectionAdvancedData(TypedDict, total=False):
    """Loaded advanced values for connection elements."""

    efficiency_source_target: NotRequired[NDArray[np.floating[Any]] | float]  # Loaded efficiency ratio per period (0-1)
    efficiency_target_source: NotRequired[NDArray[np.floating[Any]] | float]  # Loaded efficiency ratio per period (0-1)
    price_source_target: NotRequired[NDArray[np.floating[Any]] | float]  # Loaded price per period ($/kWh)
    price_target_source: NotRequired[NDArray[np.floating[Any]] | float]  # Loaded price per period ($/kWh)


class ConnectionConfigData(TypedDict):
    """Connection element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["connection"]
    basic: ConnectionBasicData
    limits: ConnectionLimitsData
    advanced: ConnectionAdvancedData
