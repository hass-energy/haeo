"""Test battery config flow."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.battery import (
    CONF_CAPACITY,
    CONF_CHARGE_COST,
    CONF_DISCHARGE_COST,
    CONF_EFFICIENCY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_POWER,
    CONF_MAX_DISCHARGE_POWER,
    CONF_MIN_CHARGE_PERCENTAGE,
)

# Test data for battery flow
VALID_DATA = [
    {
        "description": "Basic battery configuration",
        "config": {
            CONF_NAME: "Test Battery",
            CONF_CAPACITY: 10000,
            CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_soc",
            CONF_MAX_CHARGE_POWER: 5000,
            CONF_MAX_DISCHARGE_POWER: 5000,
            CONF_CHARGE_COST: 0.0,
            CONF_DISCHARGE_COST: 0.0,
        },
    },
    {
        "description": "Advanced battery configuration with efficiency and limits",
        "config": {
            CONF_NAME: "Advanced Battery",
            CONF_CAPACITY: 10000,
            CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_soc",
            CONF_MIN_CHARGE_PERCENTAGE: 10,
            CONF_MAX_CHARGE_PERCENTAGE: 90,
            CONF_MAX_CHARGE_POWER: 5000,
            CONF_MAX_DISCHARGE_POWER: 5000,
            CONF_EFFICIENCY: 0.95,
            CONF_CHARGE_COST: 0.05,
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
            CONF_CHARGE_COST: 0.0,
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
            CONF_CHARGE_COST: 0.0,
            CONF_DISCHARGE_COST: 0.0,
        },
        "error": "value must be positive",
    },
]
