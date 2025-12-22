"""Test data and validation for battery_section flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.battery_section import CONF_CAPACITY, CONF_INITIAL_CHARGE_PERCENTAGE

# Test data for battery_section flow
VALID_DATA = [
    {
        "description": "Basic battery section configuration",
        "config": {
            CONF_NAME: "Test Section",
            CONF_CAPACITY: "sensor.battery_capacity",
            CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_soc",
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {
            CONF_NAME: "",
            CONF_CAPACITY: "sensor.battery_capacity",
            CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_soc",
        },
        "error": "cannot be empty",
    },
]
