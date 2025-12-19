"""Constants for the Home Assistant Energy Optimizer integration."""

from typing import Final, Literal

# Integration domain
DOMAIN: Final = "haeo"

# Integration types
INTEGRATION_TYPE_HUB: Final = "hub"

# Configuration keys
CONF_NAME: Final = "name"
CONF_INTEGRATION_TYPE: Final = "integration_type"
CONF_ELEMENT_TYPE: Final = "element_type"
CONF_UPDATE_INTERVAL_MINUTES: Final = "update_interval_minutes"
CONF_DEBOUNCE_SECONDS: Final = "debounce_seconds"
CONF_HORIZON_PRESET: Final = "horizon_preset"

ELEMENT_TYPE_NETWORK: Final = "network"

# Interval tier configuration (4 tiers with duration and until each)
# Each tier specifies: duration = minutes per interval, until = cumulative time in minutes
CONF_TIER_1_DURATION: Final = "tier_1_duration"
CONF_TIER_1_UNTIL: Final = "tier_1_until"
CONF_TIER_2_DURATION: Final = "tier_2_duration"
CONF_TIER_2_UNTIL: Final = "tier_2_until"
CONF_TIER_3_DURATION: Final = "tier_3_duration"
CONF_TIER_3_UNTIL: Final = "tier_3_until"
CONF_TIER_4_DURATION: Final = "tier_4_duration"
CONF_TIER_4_UNTIL: Final = "tier_4_until"

# Default tier values: (duration_minutes, until_minutes)
# Tier 1: 1 minute slices until 5 minutes → 5 periods
# Tier 2: 5 minute slices until 60 minutes → 11 periods
# Tier 3: 30 minute slices until 1440 minutes (1 day) → 46 periods
# Tier 4: 60 minute slices until 4320 minutes (3 days) → 48 periods
# Total: 110 periods covering 72 hours
DEFAULT_TIER_1_DURATION: Final = 1
DEFAULT_TIER_1_UNTIL: Final = 5
DEFAULT_TIER_2_DURATION: Final = 5
DEFAULT_TIER_2_UNTIL: Final = 60
DEFAULT_TIER_3_DURATION: Final = 30
DEFAULT_TIER_3_UNTIL: Final = 1440  # 1 day
DEFAULT_TIER_4_DURATION: Final = 60
DEFAULT_TIER_4_UNTIL: Final = 4320  # 3 days

# Other defaults
DEFAULT_UPDATE_INTERVAL_MINUTES: Final = 5  # 5 minutes default
DEFAULT_DEBOUNCE_SECONDS: Final = 2  # 2 seconds debounce window

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
