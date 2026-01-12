"""Test data and validation for solar flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.solar import (
    CONF_CONNECTION,
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_PRODUCTION,
)

# Test data for solar flow - entity-first approach
# Step 1 (mode_input): Select entities (including constant entities) for each field
# Step 2 (config): Enter constant values for fields with constant entities selected
VALID_DATA = [
    {
        "description": "Basic solar configuration with constant forecast",
        "mode_input": {
            CONF_NAME: "Test Solar",
            CONF_CONNECTION: "main_bus",
            CONF_FORECAST: ["haeo.configurable_entity"],
            CONF_PRICE_PRODUCTION: [],
            CONF_CURTAILMENT: ["haeo.configurable_entity"],
        },
        "config": {
            CONF_NAME: "Test Solar",
            CONF_CONNECTION: "main_bus",
            CONF_FORECAST: 5.0,
            CONF_CURTAILMENT: False,
        },
    },
    {
        "description": "Curtailable solar with production price",
        "mode_input": {
            CONF_NAME: "Rooftop Solar",
            CONF_CONNECTION: "main_bus",
            CONF_FORECAST: ["sensor.solar_power"],
            CONF_PRICE_PRODUCTION: ["haeo.configurable_entity"],
            CONF_CURTAILMENT: ["haeo.configurable_entity"],
        },
        "config": {
            CONF_NAME: "Rooftop Solar",
            CONF_CONNECTION: "main_bus",
            CONF_FORECAST: ["sensor.solar_power"],
            CONF_PRICE_PRODUCTION: 0.04,
            CONF_CURTAILMENT: True,
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
