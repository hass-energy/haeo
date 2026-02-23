"""Constants for the Home Assistant Energy Optimizer integration."""

from typing import Final, Literal

from custom_components.haeo.core.const import CONF_ADVANCED_MODE as CONF_ADVANCED_MODE  # noqa: PLC0414
from custom_components.haeo.core.const import CONF_DEBOUNCE_SECONDS as CONF_DEBOUNCE_SECONDS  # noqa: PLC0414
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE as CONF_ELEMENT_TYPE  # noqa: PLC0414
from custom_components.haeo.core.const import CONF_HORIZON_PRESET as CONF_HORIZON_PRESET  # noqa: PLC0414
from custom_components.haeo.core.const import CONF_NAME as CONF_NAME  # noqa: PLC0414
from custom_components.haeo.core.const import CONF_TIER_1_COUNT as CONF_TIER_1_COUNT  # noqa: PLC0414
from custom_components.haeo.core.const import CONF_TIER_1_DURATION as CONF_TIER_1_DURATION  # noqa: PLC0414
from custom_components.haeo.core.const import CONF_TIER_2_COUNT as CONF_TIER_2_COUNT  # noqa: PLC0414
from custom_components.haeo.core.const import CONF_TIER_2_DURATION as CONF_TIER_2_DURATION  # noqa: PLC0414
from custom_components.haeo.core.const import CONF_TIER_3_COUNT as CONF_TIER_3_COUNT  # noqa: PLC0414
from custom_components.haeo.core.const import CONF_TIER_3_DURATION as CONF_TIER_3_DURATION  # noqa: PLC0414
from custom_components.haeo.core.const import CONF_TIER_4_COUNT as CONF_TIER_4_COUNT  # noqa: PLC0414
from custom_components.haeo.core.const import CONF_TIER_4_DURATION as CONF_TIER_4_DURATION  # noqa: PLC0414
from custom_components.haeo.core.const import DEFAULT_DEBOUNCE_SECONDS as DEFAULT_DEBOUNCE_SECONDS  # noqa: PLC0414
from custom_components.haeo.core.const import DEFAULT_TIER_1_COUNT as DEFAULT_TIER_1_COUNT  # noqa: PLC0414
from custom_components.haeo.core.const import DEFAULT_TIER_1_DURATION as DEFAULT_TIER_1_DURATION  # noqa: PLC0414
from custom_components.haeo.core.const import DEFAULT_TIER_2_COUNT as DEFAULT_TIER_2_COUNT  # noqa: PLC0414
from custom_components.haeo.core.const import DEFAULT_TIER_2_DURATION as DEFAULT_TIER_2_DURATION  # noqa: PLC0414
from custom_components.haeo.core.const import DEFAULT_TIER_3_COUNT as DEFAULT_TIER_3_COUNT  # noqa: PLC0414
from custom_components.haeo.core.const import DEFAULT_TIER_3_DURATION as DEFAULT_TIER_3_DURATION  # noqa: PLC0414
from custom_components.haeo.core.const import DEFAULT_TIER_4_COUNT as DEFAULT_TIER_4_COUNT  # noqa: PLC0414
from custom_components.haeo.core.const import DEFAULT_TIER_4_DURATION as DEFAULT_TIER_4_DURATION  # noqa: PLC0414

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
