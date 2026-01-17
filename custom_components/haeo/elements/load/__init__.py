"""Load element for HAEO integration."""

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
from .schema import CONF_CONNECTION, CONF_FORECAST, ELEMENT_TYPE, LoadConfigData, LoadConfigSchema

__all__ = [
    # Schema
    "CONF_CONNECTION",
    "CONF_FORECAST",
    "ELEMENT_TYPE",
    # Adapter
    "LOAD_DEVICE_LOAD",
    "LOAD_DEVICE_NAMES",
    "LOAD_FORECAST_LIMIT_PRICE",
    "LOAD_OUTPUT_NAMES",
    "LOAD_POWER",
    "LoadAdapter",
    "LoadConfigData",
    "LoadConfigSchema",
    "LoadDeviceName",
    "LoadOutputName",
    "adapter",
]
