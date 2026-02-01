"""Load element for HAEO integration."""

from custom_components.haeo.sections import CONF_CONNECTION

from .adapter import (
    LOAD_DEVICE_LOAD,
    LOAD_DEVICE_NAMES,
    LOAD_FORECAST_LIMIT_PRICE,
    LOAD_OUTPUT_NAMES,
    LOAD_POWER,
    LoadAdapter,
    LoadDeviceName,
    LoadOutputName,
    adapter,
)
from .schema import (
    CONF_FORECAST,
    ELEMENT_TYPE,
    OPTIONAL_INPUT_FIELDS,
    SECTION_DETAILS,
    SECTION_FORECAST,
    LoadConfigData,
    LoadConfigSchema,
)

__all__ = [
    "CONF_CONNECTION",
    "CONF_FORECAST",
    "ELEMENT_TYPE",
    "LOAD_DEVICE_LOAD",
    "LOAD_DEVICE_NAMES",
    "LOAD_FORECAST_LIMIT_PRICE",
    "LOAD_OUTPUT_NAMES",
    "LOAD_POWER",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_DETAILS",
    "SECTION_FORECAST",
    "LoadAdapter",
    "LoadConfigData",
    "LoadConfigSchema",
    "LoadDeviceName",
    "LoadOutputName",
    "adapter",
]
