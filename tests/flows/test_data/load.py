"""Test data and validation for load flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.load import CONF_FORECAST

# Test data for load flow
VALID_DATA = [
    {
        "description": "Load with forecast sensors (variable load)",
        "config": {
            CONF_NAME: "Test Load",
            CONF_FORECAST: ["sensor.forecast1", "sensor.forecast2"],
        },
    },
    {
        "description": "Load with constant sensor (fixed load pattern)",
        "config": {
            CONF_NAME: "Constant Load",
            CONF_FORECAST: ["input_number.constant_load"],
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {CONF_NAME: "", CONF_FORECAST: ["sensor.forecast1"]},
        "error": "cannot be empty",
    },
    {
        "description": "Invalid forecast sensors should fail validation",
        "config": {CONF_NAME: "Test Load", CONF_FORECAST: "not_a_list"},
        "error": "value should be a list",
    },
    {
        "description": "Missing forecast should fail validation",
        "config": {CONF_NAME: "Test Load"},
        "error": "required key not provided",
    },
]
