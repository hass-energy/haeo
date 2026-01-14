"""Test data and validation for solar flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.solar import (
    CONF_CONNECTION,
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_PRODUCTION,
)

# Test data for solar flow - single-step with choose selector
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Basic solar configuration with constant forecast",
        "config": {
            CONF_NAME: "Test Solar",
            CONF_CONNECTION: "main_bus",
            CONF_FORECAST: {"choice": "constant", "value": 5.0},
            CONF_CURTAILMENT: {"choice": "constant", "value": False},
        },
    },
    {
        "description": "Curtailable solar with production price",
        "config": {
            CONF_NAME: "Rooftop Solar",
            CONF_CONNECTION: "main_bus",
            CONF_FORECAST: {"choice": "entity", "value": ["sensor.solar_power"]},
            CONF_PRICE_PRODUCTION: {"choice": "constant", "value": 0.04},
            CONF_CURTAILMENT: {"choice": "constant", "value": True},
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
