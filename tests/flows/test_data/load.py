"""Test data and validation for load flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.load import CONF_CONNECTION, CONF_FORECAST

# Entity ID used in tests for the configurable sentinel entity.
# In tests, the entity registry is mocked to recognize this entity by its unique_id.
TEST_CONFIGURABLE_ENTITY_ID = "haeo.configurable_entity"

# Test data for load flow
VALID_DATA = [
    {
        "description": "Load with forecast sensors (variable load)",
        "config": {
            CONF_NAME: "Test Load",
            CONF_CONNECTION: "Switchboard",
            CONF_FORECAST: ["sensor.forecast1", "sensor.forecast2"],
        },
        # Step 1: entity selection
        "mode_input": {
            CONF_NAME: "Test Load",
            CONF_CONNECTION: "Switchboard",
            CONF_FORECAST: ["sensor.forecast1", "sensor.forecast2"],
        },
        # Step 2: no constant values needed (skipped automatically)
        "values_input": {},
    },
    {
        "description": "Load with constant value",
        "config": {
            CONF_NAME: "Constant Load",
            CONF_CONNECTION: "Switchboard",
            CONF_FORECAST: 5.0,  # Constant value stored in config
        },
        # Step 1: select configurable entity
        "mode_input": {
            CONF_NAME: "Constant Load",
            CONF_CONNECTION: "Switchboard",
            CONF_FORECAST: [TEST_CONFIGURABLE_ENTITY_ID],
        },
        # Step 2: provide constant value
        "values_input": {
            CONF_FORECAST: 5.0,
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {CONF_NAME: "", CONF_CONNECTION: "Switchboard", CONF_FORECAST: ["sensor.forecast1"]},
        "error": "cannot be empty",
    },
    {
        "description": "Invalid forecast sensors should fail validation",
        "config": {CONF_NAME: "Test Load", CONF_CONNECTION: "Switchboard", CONF_FORECAST: "not_a_list"},
        "error": "value should be a list",
    },
    {
        "description": "Missing forecast should fail validation",
        "config": {CONF_NAME: "Test Load", CONF_CONNECTION: "Switchboard"},
        "error": "required key not provided",
    },
]
