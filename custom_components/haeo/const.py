"""Constants for the Home Assistant Energy Optimizer integration."""

import enum
from typing import Final, Literal

# Integration domain
DOMAIN: Final = "haeo"

# External URLs
URL_HAFO: Final = "https://hafo.haeo.io"

# Integration types
INTEGRATION_TYPE_HUB: Final = "hub"

# Configuration keys
CONF_NAME: Final = "name"
CONF_INTEGRATION_TYPE: Final = "integration_type"
CONF_ELEMENT_TYPE: Final = "element_type"
CONF_UPDATE_INTERVAL_MINUTES: Final = "update_interval_minutes"
CONF_DEBOUNCE_SECONDS: Final = "debounce_seconds"
CONF_HORIZON_PRESET: Final = "horizon_preset"
CONF_ADVANCED_MODE: Final = "advanced_mode"

ELEMENT_TYPE_NETWORK: Final = "network"

# Interval tier configuration (4 tiers with count and duration each)
# Each tier specifies: count = number of intervals, duration = minutes per interval
CONF_TIER_1_COUNT: Final = "tier_1_count"
CONF_TIER_1_DURATION: Final = "tier_1_duration"
CONF_TIER_2_COUNT: Final = "tier_2_count"
CONF_TIER_2_DURATION: Final = "tier_2_duration"
CONF_TIER_3_COUNT: Final = "tier_3_count"
CONF_TIER_3_DURATION: Final = "tier_3_duration"
CONF_TIER_4_COUNT: Final = "tier_4_count"
CONF_TIER_4_DURATION: Final = "tier_4_duration"

# Default tier values: (count, duration_minutes)
# Tier 1: 5 intervals of 1 minute = 5 minutes total
# Tier 2: 11 intervals of 5 minutes = 55 minutes total (60 min cumulative)
# Tier 3: 46 intervals of 30 minutes = 23 hours total (24 hr cumulative)
# Tier 4: 48 intervals of 60 minutes = 48 hours total (72 hr cumulative)
# Total: 110 periods covering ~72 hours
DEFAULT_TIER_1_COUNT: Final = 5
DEFAULT_TIER_1_DURATION: Final = 1
DEFAULT_TIER_2_COUNT: Final = 11
DEFAULT_TIER_2_DURATION: Final = 5
DEFAULT_TIER_3_COUNT: Final = 46
DEFAULT_TIER_3_DURATION: Final = 30
DEFAULT_TIER_4_COUNT: Final = 48
DEFAULT_TIER_4_DURATION: Final = 60

# Other defaults
DEFAULT_UPDATE_INTERVAL_MINUTES: Final = 5  # 5 minutes default
DEFAULT_DEBOUNCE_SECONDS: Final = 2  # 2 seconds debounce window

# Sentinel configurable entity for user configurable values
CONFIGURABLE_ENTITY_UNIQUE_ID: Final = "haeo_configurable_entity"

# Optimization statuses
OPTIMIZATION_STATUS_SUCCESS: Final = "success"
OPTIMIZATION_STATUS_FAILED: Final = "failed"
OPTIMIZATION_STATUS_PENDING: Final = "pending"


type NetworkOutputName = Literal[
    "network_optimization_cost",
    "network_optimization_status",
    "network_optimization_duration",
]
NETWORK_OUTPUT_NAMES: Final[frozenset[NetworkOutputName]] = frozenset(
    [
        OUTPUT_NAME_OPTIMIZATION_COST := "network_optimization_cost",
        OUTPUT_NAME_OPTIMIZATION_STATUS := "network_optimization_status",
        OUTPUT_NAME_OPTIMIZATION_DURATION := "network_optimization_duration",
    ]
)

type NetworkDeviceName = Literal["network"]

NETWORK_DEVICE_NAMES: Final[frozenset[NetworkDeviceName]] = frozenset(
    (NETWORK_DEVICE_NETWORK := "network",),
)


class ConnectivityLevel(enum.StrEnum):
    """Connectivity level for element types in connection selectors.

    - ALWAYS: Always shown in connection selectors
    - ADVANCED: Only shown when advanced mode is enabled
    - NEVER: Never shown in connection selectors
    """

    ALWAYS = enum.auto()
    ADVANCED = enum.auto()
    NEVER = enum.auto()
