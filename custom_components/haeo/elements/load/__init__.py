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
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_TARGET_SOURCE,
    ELEMENT_TYPE,
    OPTIONAL_INPUT_FIELDS,
    SECTION_COMMON,
    SECTION_CURTAILMENT,
    SECTION_FORECAST,
    SECTION_PRICING,
    LoadConfigData,
    LoadConfigSchema,
)

__all__ = [
    "CONF_CONNECTION",
    "CONF_CURTAILMENT",
    "CONF_FORECAST",
    "CONF_PRICE_TARGET_SOURCE",
    "ELEMENT_TYPE",
    "LOAD_DEVICE_LOAD",
    "LOAD_DEVICE_NAMES",
    "LOAD_FORECAST_LIMIT_PRICE",
    "LOAD_OUTPUT_NAMES",
    "LOAD_POWER",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_COMMON",
    "SECTION_CURTAILMENT",
    "SECTION_FORECAST",
    "SECTION_PRICING",
    "LoadAdapter",
    "LoadConfigData",
    "LoadConfigSchema",
    "LoadDeviceName",
    "LoadOutputName",
    "adapter",
]
