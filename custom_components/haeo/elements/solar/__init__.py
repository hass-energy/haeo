"""Solar element for HAEO integration."""

from .adapter import (
    SOLAR_DEVICE_NAMES,
    SOLAR_DEVICE_SOLAR,
    SOLAR_FORECAST_LIMIT,
    SOLAR_OUTPUT_NAMES,
    SOLAR_POWER,
    SolarAdapter,
    SolarDeviceName,
    SolarOutputName,
    adapter,
)
from .schema import (
    CONF_CONNECTION,
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_PRODUCTION,
    ELEMENT_TYPE,
    SolarConfigData,
    SolarConfigSchema,
)

__all__ = [
    "CONF_CONNECTION",
    "CONF_CURTAILMENT",
    "CONF_FORECAST",
    "CONF_PRICE_PRODUCTION",
    "ELEMENT_TYPE",
    "SOLAR_DEVICE_NAMES",
    "SOLAR_DEVICE_SOLAR",
    "SOLAR_FORECAST_LIMIT",
    "SOLAR_OUTPUT_NAMES",
    "SOLAR_POWER",
    "SolarAdapter",
    "SolarConfigData",
    "SolarConfigSchema",
    "SolarDeviceName",
    "SolarOutputName",
    "adapter",
]
