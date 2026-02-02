"""Test battery config flow data for choose selector approach."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.battery import (
    CONF_CAPACITY,
    CONF_CONFIGURE_PARTITIONS,
    CONF_CONNECTION,
    CONF_EFFICIENCY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_EFFICIENCY,
    SECTION_LIMITS,
    SECTION_PARTITIONING,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
    SECTION_STORAGE,
)

# Test data for battery flow - single-step with choose selector (plus optional partition step)
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Basic battery configuration",
        "config": {
            SECTION_COMMON: {
                CONF_NAME: "Test Battery",
                CONF_CONNECTION: "main_bus",
            },
            SECTION_STORAGE: {
                CONF_CAPACITY: 10.0,
                CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
            },
            SECTION_LIMITS: {
                CONF_MIN_CHARGE_PERCENTAGE: 10.0,
                CONF_MAX_CHARGE_PERCENTAGE: 90.0,
            },
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_TARGET_SOURCE: 5.0,
                CONF_MAX_POWER_SOURCE_TARGET: 5.0,
            },
            SECTION_PRICING: {
                CONF_PRICE_TARGET_SOURCE: 0.01,
            },
            SECTION_EFFICIENCY: {
                CONF_EFFICIENCY: 95.0,
            },
            SECTION_PARTITIONING: {
                CONF_CONFIGURE_PARTITIONS: False,
            },
        },
    },
    {
        "description": "Battery with optional discharge cost",
        "config": {
            SECTION_COMMON: {
                CONF_NAME: "Advanced Battery",
                CONF_CONNECTION: "main_bus",
            },
            SECTION_STORAGE: {
                CONF_CAPACITY: 10.0,
                CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
            },
            SECTION_LIMITS: {
                CONF_MIN_CHARGE_PERCENTAGE: 10.0,
                CONF_MAX_CHARGE_PERCENTAGE: 90.0,
            },
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_TARGET_SOURCE: 5.0,
                CONF_MAX_POWER_SOURCE_TARGET: 5.0,
            },
            SECTION_PRICING: {
                CONF_PRICE_TARGET_SOURCE: 0.05,
                CONF_PRICE_SOURCE_TARGET: 0.03,
            },
            SECTION_EFFICIENCY: {
                CONF_EFFICIENCY: 95.0,
            },
            SECTION_PARTITIONING: {
                CONF_CONFIGURE_PARTITIONS: False,
            },
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {
            SECTION_COMMON: {
                CONF_NAME: "",
                CONF_CONNECTION: "main_bus",
            },
            SECTION_STORAGE: {
                CONF_CAPACITY: 10.0,
                CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
            },
            SECTION_LIMITS: {
            },
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_TARGET_SOURCE: 5.0,
                CONF_MAX_POWER_SOURCE_TARGET: 5.0,
            },
            SECTION_PRICING: {
                CONF_PRICE_TARGET_SOURCE: 0.01,
            },
            SECTION_EFFICIENCY: {
                CONF_EFFICIENCY: 95.0,
            },
            SECTION_PARTITIONING: {
                CONF_CONFIGURE_PARTITIONS: False,
            },
        },
        "error": "cannot be empty",
    },
]
