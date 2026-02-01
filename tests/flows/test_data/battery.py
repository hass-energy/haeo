"""Test battery config flow data for choose selector approach."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.battery import (
    CONF_CAPACITY,
    CONF_CONFIGURE_PARTITIONS,
    CONF_CONNECTION,
    CONF_DISCHARGE_COST,
    CONF_EARLY_CHARGE_INCENTIVE,
    CONF_EFFICIENCY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_POWER,
    CONF_MAX_DISCHARGE_POWER,
    CONF_MIN_CHARGE_PERCENTAGE,
    SECTION_ADVANCED,
    SECTION_DETAILS,
    SECTION_LIMITS,
    SECTION_PRICING,
    SECTION_STORAGE,
)

# Test data for battery flow - single-step with choose selector (plus optional partition step)
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Basic battery configuration",
        "config": {
            SECTION_DETAILS: {
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
                CONF_MAX_CHARGE_POWER: 5.0,
                CONF_MAX_DISCHARGE_POWER: 5.0,
            },
            SECTION_PRICING: {
                CONF_EARLY_CHARGE_INCENTIVE: 0.01,
            },
            SECTION_ADVANCED: {
                CONF_EFFICIENCY: 95.0,
                CONF_CONFIGURE_PARTITIONS: False,
            },
        },
    },
    {
        "description": "Battery with optional discharge cost",
        "config": {
            SECTION_DETAILS: {
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
                CONF_MAX_CHARGE_POWER: 5.0,
                CONF_MAX_DISCHARGE_POWER: 5.0,
            },
            SECTION_PRICING: {
                CONF_EARLY_CHARGE_INCENTIVE: 0.05,
                CONF_DISCHARGE_COST: 0.03,
            },
            SECTION_ADVANCED: {
                CONF_EFFICIENCY: 95.0,
                CONF_CONFIGURE_PARTITIONS: False,
            },
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {
            SECTION_DETAILS: {
                CONF_NAME: "",
                CONF_CONNECTION: "main_bus",
            },
            SECTION_STORAGE: {
                CONF_CAPACITY: 10.0,
                CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
            },
            SECTION_LIMITS: {
                CONF_MAX_CHARGE_POWER: 5.0,
                CONF_MAX_DISCHARGE_POWER: 5.0,
            },
            SECTION_PRICING: {
                CONF_EARLY_CHARGE_INCENTIVE: 0.01,
            },
            SECTION_ADVANCED: {
                CONF_EFFICIENCY: 95.0,
                CONF_CONFIGURE_PARTITIONS: False,
            },
        },
        "error": "cannot be empty",
    },
]
