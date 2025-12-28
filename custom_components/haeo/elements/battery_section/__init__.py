"""Battery section element for HAEO integration."""

from .adapter import (
    BATTERY_SECTION_DEVICE,
    BATTERY_SECTION_DEVICE_NAMES,
    BATTERY_SECTION_ENERGY_IN_FLOW,
    BATTERY_SECTION_ENERGY_OUT_FLOW,
    BATTERY_SECTION_ENERGY_STORED,
    BATTERY_SECTION_OUTPUT_NAMES,
    BATTERY_SECTION_POWER_ACTIVE,
    BATTERY_SECTION_POWER_BALANCE,
    BATTERY_SECTION_POWER_CHARGE,
    BATTERY_SECTION_POWER_DISCHARGE,
    BATTERY_SECTION_SOC_MAX,
    BATTERY_SECTION_SOC_MIN,
    BatterySectionAdapter,
    BatterySectionDeviceName,
    BatterySectionOutputName,
    adapter,
)
from .flow import BatterySectionSubentryFlowHandler
from .schema import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE,
    ELEMENT_TYPE,
    BatterySectionConfigData,
    BatterySectionConfigSchema,
)

__all__ = [
    # Adapter
    "BATTERY_SECTION_DEVICE",
    "BATTERY_SECTION_DEVICE_NAMES",
    "BATTERY_SECTION_ENERGY_IN_FLOW",
    "BATTERY_SECTION_ENERGY_OUT_FLOW",
    "BATTERY_SECTION_ENERGY_STORED",
    "BATTERY_SECTION_OUTPUT_NAMES",
    "BATTERY_SECTION_POWER_ACTIVE",
    "BATTERY_SECTION_POWER_BALANCE",
    "BATTERY_SECTION_POWER_CHARGE",
    "BATTERY_SECTION_POWER_DISCHARGE",
    "BATTERY_SECTION_SOC_MAX",
    "BATTERY_SECTION_SOC_MIN",
    "BatterySectionAdapter",
    "adapter",
    # Schema
    "CONF_CAPACITY",
    "CONF_INITIAL_CHARGE",
    "ELEMENT_TYPE",
    "BatterySectionConfigData",
    "BatterySectionConfigSchema",
    "BatterySectionDeviceName",
    "BatterySectionOutputName",
    # Flow
    "BatterySectionSubentryFlowHandler",
]
