"""Test battery config flow."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.battery import (
    CONF_CAPACITY,
    CONF_CONNECTION,
    CONF_DISCHARGE_COST,
    CONF_EARLY_CHARGE_INCENTIVE,
    CONF_EFFICIENCY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_POWER,
    CONF_MAX_DISCHARGE_POWER,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_OVERCHARGE_PERCENTAGE,
    CONF_UNDERCHARGE_PERCENTAGE,
)
from custom_components.haeo.flows.field_schema import MODE_SUFFIX, InputMode

# Test data for battery flow
VALID_DATA = [
    {
        "description": "Basic battery configuration",
        "mode_input": {
            CONF_NAME: "Test Battery",
            CONF_CONNECTION: "main_bus",
            f"{CONF_CAPACITY}{MODE_SUFFIX}": InputMode.CONSTANT,
            f"{CONF_INITIAL_CHARGE_PERCENTAGE}{MODE_SUFFIX}": InputMode.ENTITY_LINK,
            f"{CONF_MIN_CHARGE_PERCENTAGE}{MODE_SUFFIX}": InputMode.NONE,
            f"{CONF_MAX_CHARGE_PERCENTAGE}{MODE_SUFFIX}": InputMode.NONE,
            f"{CONF_EFFICIENCY}{MODE_SUFFIX}": InputMode.NONE,
            f"{CONF_MAX_CHARGE_POWER}{MODE_SUFFIX}": InputMode.CONSTANT,
            f"{CONF_MAX_DISCHARGE_POWER}{MODE_SUFFIX}": InputMode.CONSTANT,
            f"{CONF_EARLY_CHARGE_INCENTIVE}{MODE_SUFFIX}": InputMode.CONSTANT,
            f"{CONF_DISCHARGE_COST}{MODE_SUFFIX}": InputMode.CONSTANT,
            f"{CONF_UNDERCHARGE_PERCENTAGE}{MODE_SUFFIX}": InputMode.NONE,
            f"{CONF_OVERCHARGE_PERCENTAGE}{MODE_SUFFIX}": InputMode.NONE,
        },
        "config": {
            CONF_NAME: "Test Battery",
            CONF_CAPACITY: 10000,
            CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
            CONF_MAX_CHARGE_POWER: 5000,
            CONF_MAX_DISCHARGE_POWER: 5000,
            CONF_EARLY_CHARGE_INCENTIVE: 0.001,
            CONF_DISCHARGE_COST: 0.0,
        },
    },
    {
        "description": "Advanced battery configuration with efficiency and limits",
        "mode_input": {
            CONF_NAME: "Advanced Battery",
            CONF_CONNECTION: "main_bus",
            f"{CONF_CAPACITY}{MODE_SUFFIX}": InputMode.CONSTANT,
            f"{CONF_INITIAL_CHARGE_PERCENTAGE}{MODE_SUFFIX}": InputMode.ENTITY_LINK,
            f"{CONF_MIN_CHARGE_PERCENTAGE}{MODE_SUFFIX}": InputMode.CONSTANT,
            f"{CONF_MAX_CHARGE_PERCENTAGE}{MODE_SUFFIX}": InputMode.CONSTANT,
            f"{CONF_EFFICIENCY}{MODE_SUFFIX}": InputMode.CONSTANT,
            f"{CONF_MAX_CHARGE_POWER}{MODE_SUFFIX}": InputMode.CONSTANT,
            f"{CONF_MAX_DISCHARGE_POWER}{MODE_SUFFIX}": InputMode.CONSTANT,
            f"{CONF_EARLY_CHARGE_INCENTIVE}{MODE_SUFFIX}": InputMode.CONSTANT,
            f"{CONF_DISCHARGE_COST}{MODE_SUFFIX}": InputMode.CONSTANT,
            f"{CONF_UNDERCHARGE_PERCENTAGE}{MODE_SUFFIX}": InputMode.NONE,
            f"{CONF_OVERCHARGE_PERCENTAGE}{MODE_SUFFIX}": InputMode.NONE,
        },
        "config": {
            CONF_NAME: "Advanced Battery",
            CONF_CAPACITY: 10000,
            CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
            CONF_MIN_CHARGE_PERCENTAGE: 10,
            CONF_MAX_CHARGE_PERCENTAGE: 90,
            CONF_MAX_CHARGE_POWER: 5000,
            CONF_MAX_DISCHARGE_POWER: 5000,
            CONF_EFFICIENCY: 0.95,
            CONF_EARLY_CHARGE_INCENTIVE: 0.05,
            CONF_DISCHARGE_COST: 0.03,
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {
            CONF_NAME: "",
            CONF_CAPACITY: 5000,
            CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_soc",
            CONF_MAX_CHARGE_POWER: 5000,
            CONF_MAX_DISCHARGE_POWER: 5000,
            CONF_EARLY_CHARGE_INCENTIVE: 0.001,
            CONF_DISCHARGE_COST: 0.0,
        },
        "error": "cannot be empty",
    },
    {
        "description": "Negative capacity should fail validation",
        "config": {
            CONF_NAME: "Test Battery",
            CONF_CAPACITY: -1000,
            CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_soc",
            CONF_MAX_CHARGE_POWER: 5000,
            CONF_MAX_DISCHARGE_POWER: 5000,
            CONF_EARLY_CHARGE_INCENTIVE: 0.001,
            CONF_DISCHARGE_COST: 0.0,
        },
        "error": "value must be positive",
    },
]
