"""Network element for HAEO integration.

The Network element represents the overall optimization network.
It is auto-created and provides network-level outputs like
optimization cost, status, and duration.
"""

# Re-export output names from model for convenience
from custom_components.haeo.model import (
    NETWORK_OPTIMIZATION_COST,
    NETWORK_OPTIMIZATION_DURATION,
    NETWORK_OPTIMIZATION_STATUS,
    NetworkOutputName,
)

from .adapter import (
    NETWORK_DEVICE_NAMES,
    NETWORK_DEVICE_NETWORK,
    NETWORK_OUTPUT_NAMES,
    NetworkAdapter,
    NetworkDeviceName,
    NetworkSubentryFlowHandler,
    adapter,
)
from .schema import ELEMENT_TYPE, ElementTypeName, NetworkConfigData, NetworkConfigSchema

__all__ = [
    "ELEMENT_TYPE",
    "NETWORK_DEVICE_NAMES",
    "NETWORK_DEVICE_NETWORK",
    "NETWORK_OPTIMIZATION_COST",
    "NETWORK_OPTIMIZATION_DURATION",
    "NETWORK_OPTIMIZATION_STATUS",
    "NETWORK_OUTPUT_NAMES",
    "ElementTypeName",
    "NetworkAdapter",
    "NetworkConfigData",
    "NetworkConfigSchema",
    "NetworkDeviceName",
    "NetworkOutputName",
    "NetworkSubentryFlowHandler",
    "adapter",
]
