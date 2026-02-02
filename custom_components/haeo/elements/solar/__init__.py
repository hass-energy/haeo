"""Solar element for HAEO integration."""

from custom_components.haeo.sections import CONF_CONNECTION

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
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_SOURCE_TARGET,
    ELEMENT_TYPE,
    OPTIONAL_INPUT_FIELDS,
    SECTION_ADVANCED,
    SECTION_COMMON,
    SECTION_FORECAST,
    SECTION_PRICING,
    SolarConfigData,
    SolarConfigSchema,
)

__all__ = [
    "CONF_CONNECTION",
    "CONF_CURTAILMENT",
    "CONF_FORECAST",
    "CONF_PRICE_SOURCE_TARGET",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_ADVANCED",
    "SECTION_COMMON",
    "SECTION_FORECAST",
    "SECTION_PRICING",
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
