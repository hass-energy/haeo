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
from .flow import SolarSubentryFlowHandler
from .schema import (
    CONF_CONNECTION,
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_PRODUCTION,
    DEFAULTS,
    ELEMENT_TYPE,
    INPUT_FIELDS,
    ElementTypeName,
    SolarConfigData,
    SolarConfigSchema,
)

__all__ = [
    "CONF_CONNECTION",
    "CONF_CURTAILMENT",
    "CONF_FORECAST",
    "CONF_PRICE_PRODUCTION",
    "DEFAULTS",
    "ELEMENT_TYPE",
    "INPUT_FIELDS",
    "SOLAR_DEVICE_NAMES",
    "SOLAR_DEVICE_SOLAR",
    "SOLAR_FORECAST_LIMIT",
    "SOLAR_OUTPUT_NAMES",
    "SOLAR_POWER",
    "ElementTypeName",
    "SolarAdapter",
    "SolarConfigData",
    "SolarConfigSchema",
    "SolarDeviceName",
    "SolarOutputName",
    "SolarSubentryFlowHandler",
    "adapter",
]
