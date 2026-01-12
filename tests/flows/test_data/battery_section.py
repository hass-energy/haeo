"""Test data and validation for battery_section flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.battery_section import CONF_CAPACITY, CONF_INITIAL_CHARGE

# Test data for battery_section flow - entity-first approach
# Step 1 (mode_input): Select entities (including constant entities) for each field
# Step 2 (config): Enter constant values for fields with constant entities selected
VALID_DATA = [
    {
        "description": "Battery section with sensor entities",
        "mode_input": {
            CONF_NAME: "Test Section",
            CONF_CAPACITY: ["sensor.battery_capacity"],
            CONF_INITIAL_CHARGE: ["sensor.battery_charge"],
        },
        "config": {
            CONF_NAME: "Test Section",
            CONF_CAPACITY: ["sensor.battery_capacity"],
            CONF_INITIAL_CHARGE: ["sensor.battery_charge"],
        },
    },
    {
        "description": "Battery section with constant values",
        "mode_input": {
            CONF_NAME: "Constant Section",
            CONF_CAPACITY: ["haeo.configurable_entity"],
            CONF_INITIAL_CHARGE: ["haeo.configurable_entity"],
        },
        "config": {
            CONF_NAME: "Constant Section",
            CONF_CAPACITY: 10.0,
            CONF_INITIAL_CHARGE: 5.0,
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
