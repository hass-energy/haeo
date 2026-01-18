"""Connection element for HAEO integration."""

# Re-export connection output names from model
from custom_components.haeo.model.elements.connection import (
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
    CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
    CONNECTION_TIME_SLICE,
)
from custom_components.haeo.model.elements.connection import ConnectionOutputName as ModelConnectionOutputName

from .adapter import (
    CONNECTION_DEVICE_CONNECTION,
    CONNECTION_DEVICE_NAMES,
    CONNECTION_OUTPUT_NAMES,
    CONNECTION_POWER_ACTIVE,
    ConnectionAdapter,
    ConnectionDeviceName,
    ConnectionOutputName,
    adapter,
)
from .schema import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    CONF_SOURCE,
    CONF_TARGET,
    ELEMENT_TYPE,
    ConnectionConfigData,
    ConnectionConfigSchema,
)

__all__ = [
    "CONF_EFFICIENCY_SOURCE_TARGET",
    "CONF_EFFICIENCY_TARGET_SOURCE",
    "CONF_MAX_POWER_SOURCE_TARGET",
    "CONF_MAX_POWER_TARGET_SOURCE",
    "CONF_PRICE_SOURCE_TARGET",
    "CONF_PRICE_TARGET_SOURCE",
    "CONF_SOURCE",
    "CONF_TARGET",
    "CONNECTION_DEVICE_CONNECTION",
    "CONNECTION_DEVICE_NAMES",
    "CONNECTION_OUTPUT_NAMES",
    "CONNECTION_POWER_ACTIVE",
    "CONNECTION_POWER_SOURCE_TARGET",
    "CONNECTION_POWER_TARGET_SOURCE",
    "CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET",
    "CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE",
    "CONNECTION_TIME_SLICE",
    "ELEMENT_TYPE",
    "ConnectionAdapter",
    "ConnectionConfigData",
    "ConnectionConfigSchema",
    "ConnectionDeviceName",
    "ConnectionOutputName",
    "ModelConnectionOutputName",
    "adapter",
]
