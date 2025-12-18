"""Test data and validation for solar flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.solar import CONF_CURTAILMENT, CONF_FORECAST, CONF_PRICE_PRODUCTION

# Test data for solar flow
VALID_DATA = [
    {
        "description": "Basic solar configuration",
        "config": {
            CONF_NAME: "Test Solar",
            CONF_FORECAST: ["sensor.solar_power"],
            CONF_CURTAILMENT: False,
        },
    },
    {
        "description": "Curtailable solar configuration",
        "config": {
            CONF_NAME: "Curtailable Solar",
            CONF_FORECAST: ["sensor.solar_power"],
            CONF_CURTAILMENT: True,
            CONF_PRICE_PRODUCTION: 0.03,
        },
    },
    {
        "description": "Solar with forecast sensors",
        "config": {
            CONF_NAME: "Rooftop Solar",
            CONF_FORECAST: ["sensor.solar_power"],
            CONF_CURTAILMENT: True,
            CONF_PRICE_PRODUCTION: 0.04,
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {CONF_NAME: "", CONF_FORECAST: ["sensor.test"]},
        "error": "cannot be empty",
    },
    {
        "description": "Invalid forecast sensors should fail validation",
        "config": {CONF_NAME: "Test", CONF_FORECAST: "not_a_list", CONF_CURTAILMENT: False},
        "error": "value should be a list",
    },
]
