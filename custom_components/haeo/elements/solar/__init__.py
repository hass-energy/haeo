"""Solar element for HAEO integration."""

from .adapter import (
    SOLAR_DEVICE_NAMES,
    SOLAR_DEVICE_SOLAR,
    SOLAR_FORECAST_LIMIT,
    SOLAR_OUTPUT_NAMES,
    SOLAR_POWER,
    SOLAR_POWER_AVAILABLE,
    SOLAR_PRICE,
    SolarAdapter,
    SolarDeviceName,
    SolarOutputName,
    adapter,
)
from .flow import SolarSubentryFlowHandler
from .schema import (
    CONF_CONNECTION,
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_PRODUCTION,
    DEFAULTS,
    ELEMENT_TYPE,
    SolarConfigData,
    SolarConfigSchema,
)

__all__ = [
    # Schema
    "CONF_CONNECTION",
    "CONF_CURTAILMENT",
    "CONF_FORECAST",
    "CONF_PRICE_PRODUCTION",
    "DEFAULTS",
    "ELEMENT_TYPE",
    # Adapter
    "SOLAR_DEVICE_NAMES",
    "SOLAR_DEVICE_SOLAR",
    "SOLAR_FORECAST_LIMIT",
    "SOLAR_OUTPUT_NAMES",
    "SOLAR_POWER",
    "SOLAR_POWER_AVAILABLE",
    "SOLAR_PRICE",
    "SolarAdapter",
    "SolarConfigData",
    "SolarConfigSchema",
    "SolarDeviceName",
    "SolarOutputName",
    # Flow
    "SolarSubentryFlowHandler",
    "adapter",
]
