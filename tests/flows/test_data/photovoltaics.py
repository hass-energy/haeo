"""Test data and validation for photovoltaics flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.photovoltaics import CONF_CURTAILMENT, CONF_FORECAST, CONF_PRICE_PRODUCTION

# Test data for photovoltaics flow
VALID_DATA = [
    {
        "description": "Basic photovoltaics configuration",
        "config": {
            CONF_NAME: "Test Photovoltaics",
            CONF_FORECAST: ["sensor.solar_power"],
            CONF_CURTAILMENT: False,
        },
    },
    {
        "description": "Curtailable photovoltaics configuration",
        "config": {
            CONF_NAME: "Curtailable Photovoltaics",
            CONF_FORECAST: ["sensor.solar_power"],
            CONF_CURTAILMENT: True,
            CONF_PRICE_PRODUCTION: 0.03,
        },
    },
    {
        "description": "Photovoltaics with forecast sensors",
        "config": {
            CONF_NAME: "Solar Photovoltaics",
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
