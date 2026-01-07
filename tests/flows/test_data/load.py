"""Test data and validation for load flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.load import CONF_CONNECTION, CONF_FORECAST

# Test data for load flow - entity-first approach
# Step 1 (mode_input): Select entities (including constant entities) for each field
# Step 2 (config): Enter constant values for fields with constant entities selected
VALID_DATA = [
    {
        "description": "Load with forecast sensors (variable load)",
        "mode_input": {
            CONF_NAME: "Test Load",
            CONF_CONNECTION: "main_bus",
            CONF_FORECAST: ["sensor.forecast1", "sensor.forecast2"],
        },
        "config": {
            CONF_NAME: "Test Load",
            CONF_CONNECTION: "main_bus",
            CONF_FORECAST: ["sensor.forecast1", "sensor.forecast2"],
        },
    },
    {
        "description": "Load with constant value (fixed load pattern)",
        "mode_input": {
            CONF_NAME: "Constant Load",
            CONF_CONNECTION: "main_bus",
            CONF_FORECAST: ["sensor.haeo_constant_power"],
        },
        "config": {
            CONF_NAME: "Constant Load",
            CONF_CONNECTION: "main_bus",
            CONF_FORECAST: 1.5,
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
