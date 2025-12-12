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

ELEMENT_TYPE_NETWORK: Final = "network"

type NetworkDeviceName = Literal["network"]

# Horizon and period configuration
CONF_HORIZON_HOURS: Final = "horizon_hours"
CONF_PERIOD_MINUTES: Final = "period_minutes"
DEFAULT_HORIZON_HOURS: Final = 48  # 48 hours default
DEFAULT_PERIOD_MINUTES: Final = 5  # 5 minutes default
DEFAULT_UPDATE_INTERVAL_MINUTES: Final = 5  # 5 minutes default
DEFAULT_DEBOUNCE_SECONDS: Final = 2  # 2 seconds debounce window

# Optimization statuses
OPTIMIZATION_STATUS_SUCCESS: Final = "success"
OPTIMIZATION_STATUS_FAILED: Final = "failed"
OPTIMIZATION_STATUS_PENDING: Final = "pending"

# Network output names
OUTPUT_NAME_OPTIMIZATION_COST: Final = "network_optimization_cost"
OUTPUT_NAME_OPTIMIZATION_STATUS: Final = "network_optimization_status"
OUTPUT_NAME_OPTIMIZATION_DURATION: Final = "network_optimization_duration"

type NetworkOutputName = Literal[
    "network_optimization_cost",
    "network_optimization_status",
    "network_optimization_duration",
]

NETWORK_OUTPUT_NAMES: Final[frozenset[NetworkOutputName]] = frozenset(
    [
        OUTPUT_NAME_OPTIMIZATION_COST,
        OUTPUT_NAME_OPTIMIZATION_STATUS,
        OUTPUT_NAME_OPTIMIZATION_DURATION,
    ]
)
