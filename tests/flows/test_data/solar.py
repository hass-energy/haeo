"""Test data and validation for solar flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.solar import (
    CONF_CONNECTION,
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_PRODUCTION,
)

# Test data for solar flow
VALID_DATA = [
    {
        "description": "Basic solar configuration",
        "config": {
            CONF_NAME: "Test Solar",
            CONF_CONNECTION: "Switchboard",
            CONF_FORECAST: ["sensor.solar_power"],
            CONF_CURTAILMENT: False,
        },
        "mode_input": {
            CONF_NAME: "Test Solar",
            CONF_CONNECTION: "Switchboard",
            CONF_FORECAST: ["sensor.solar_power"],
            CONF_CURTAILMENT: False,
        },
        "values_input": {},
    },
    {
        "description": "Curtailable solar configuration",
        "config": {
            CONF_NAME: "Curtailable Solar",
            CONF_CONNECTION: "Switchboard",
            CONF_FORECAST: ["sensor.solar_power"],
            CONF_CURTAILMENT: True,
            CONF_PRICE_PRODUCTION: 0.03,
        },
        "mode_input": {
            CONF_NAME: "Curtailable Solar",
            CONF_CONNECTION: "Switchboard",
            CONF_FORECAST: ["sensor.solar_power"],
            CONF_CURTAILMENT: True,
            CONF_PRICE_PRODUCTION: 0.03,
        },
        "values_input": {},
    },
    {
        "description": "Solar with forecast sensors",
        "config": {
            CONF_NAME: "Rooftop Solar",
            CONF_CONNECTION: "Switchboard",
            CONF_FORECAST: ["sensor.solar_power"],
            CONF_CURTAILMENT: True,
            CONF_PRICE_PRODUCTION: 0.04,
        },
        "mode_input": {
            CONF_NAME: "Rooftop Solar",
            CONF_CONNECTION: "Switchboard",
            CONF_FORECAST: ["sensor.solar_power"],
            CONF_CURTAILMENT: True,
            CONF_PRICE_PRODUCTION: 0.04,
        },
        "values_input": {},
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {CONF_NAME: "", CONF_CONNECTION: "Switchboard", CONF_FORECAST: ["sensor.test"]},
        "error": "cannot be empty",
    },
    {
        "description": "Invalid forecast sensors should fail validation",
        "config": {
            CONF_NAME: "Test",
            CONF_CONNECTION: "Switchboard",
            CONF_FORECAST: "not_a_list",
            CONF_CURTAILMENT: False,
        },
        "error": "value should be a list",
    },
]
