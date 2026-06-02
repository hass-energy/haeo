"""Constants for the Home Assistant Energy Optimizer integration."""

from typing import Final, Literal

# Integration domain
DOMAIN: Final = "haeo"

# External URLs
URL_HAFO: Final = "https://hafo.haeo.io"

# Integration types
INTEGRATION_TYPE_HUB: Final = "hub"

# Configuration keys
CONF_INTEGRATION_TYPE: Final = "integration_type"
CONF_RECORD_FORECASTS: Final = "record_forecasts"

ELEMENT_TYPE_NETWORK: Final = "network"

# Static frontend resources
#
# Each Lovelace card is served as its own fully self-contained bundle and
# registered as a separate frontend resource. Keeping the cards independent
# (no shared chunks or cross-file imports) ensures one card's bundle can never
# break registration of another when browser or service-worker caches differ.
STATIC_CARD_STATIC_PATH: Final = "/haeo-static"
STATIC_CARD_STATIC_DIR: Final = "www"

# (relative file path under the integration directory, served URL path)
STATIC_CARD_BUNDLES: Final[tuple[tuple[str, str], ...]] = (
    ("www/haeo-forecast-card.min.js", "/haeo-static/haeo-forecast-card.min.js"),
    ("www/haeo-topology-card.min.js", "/haeo-static/haeo-topology-card.min.js"),
)

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

# Horizon entity unique ID suffix
OUTPUT_NAME_HORIZON: Final = "horizon"

type NetworkDeviceName = Literal["network"]

NETWORK_DEVICE_NAMES: Final[frozenset[NetworkDeviceName]] = frozenset(
    (NETWORK_DEVICE_NETWORK := "network",),
)
