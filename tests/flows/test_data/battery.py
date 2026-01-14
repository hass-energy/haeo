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
)

# Test data for battery flow - single-step with choose selector (plus optional partition step)
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Basic battery configuration",
        "config": {
            CONF_NAME: "Test Battery",
            CONF_CONNECTION: "main_bus",
            CONF_CAPACITY: {"choice": "constant", "value": 10.0},
            CONF_INITIAL_CHARGE_PERCENTAGE: {"choice": "entity", "value": ["sensor.battery_soc"]},
            CONF_MIN_CHARGE_PERCENTAGE: {"choice": "constant", "value": 10.0},
            CONF_MAX_CHARGE_PERCENTAGE: {"choice": "constant", "value": 90.0},
            CONF_EFFICIENCY: {"choice": "constant", "value": 95.0},
            CONF_MAX_CHARGE_POWER: {"choice": "constant", "value": 5.0},
            CONF_MAX_DISCHARGE_POWER: {"choice": "constant", "value": 5.0},
            CONF_EARLY_CHARGE_INCENTIVE: {"choice": "constant", "value": 0.01},
            CONF_CONFIGURE_PARTITIONS: False,
        },
    },
    {
        "description": "Battery with optional discharge cost",
        "config": {
            CONF_NAME: "Advanced Battery",
            CONF_CONNECTION: "main_bus",
            CONF_CAPACITY: {"choice": "constant", "value": 10.0},
            CONF_INITIAL_CHARGE_PERCENTAGE: {"choice": "entity", "value": ["sensor.battery_soc"]},
            CONF_MIN_CHARGE_PERCENTAGE: {"choice": "constant", "value": 10.0},
            CONF_MAX_CHARGE_PERCENTAGE: {"choice": "constant", "value": 90.0},
            CONF_MAX_CHARGE_POWER: {"choice": "constant", "value": 5.0},
            CONF_MAX_DISCHARGE_POWER: {"choice": "constant", "value": 5.0},
            CONF_EFFICIENCY: {"choice": "constant", "value": 95.0},
            CONF_EARLY_CHARGE_INCENTIVE: {"choice": "constant", "value": 0.05},
            CONF_DISCHARGE_COST: {"choice": "constant", "value": 0.03},
            CONF_CONFIGURE_PARTITIONS: False,
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {
            CONF_NAME: "",
            CONF_CONNECTION: "main_bus",
            CONF_CAPACITY: {"choice": "constant", "value": 10.0},
            CONF_INITIAL_CHARGE_PERCENTAGE: {"choice": "entity", "value": ["sensor.battery_soc"]},
            CONF_MAX_CHARGE_POWER: {"choice": "constant", "value": 5.0},
            CONF_MAX_DISCHARGE_POWER: {"choice": "constant", "value": 5.0},
            CONF_CONFIGURE_PARTITIONS: False,
        },
        "error": "cannot be empty",
    },
]
