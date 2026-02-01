"""Test data and validation for solar flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.solar import (
    CONF_CONNECTION,
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_PRODUCTION,
    SECTION_ADVANCED,
    SECTION_BASIC,
    SECTION_INPUTS,
    SECTION_PRICING,
)

# Test data for solar flow - single-step with choose selector
# config: Contains all field values in choose selector format
# Note: price_production and curtailment have force_required=True, so they must be included
VALID_DATA = [
    {
        "description": "Basic solar configuration with constant forecast",
        "config": {
            SECTION_BASIC: {
                CONF_NAME: "Test Solar",
                CONF_CONNECTION: "main_bus",
            },
            SECTION_INPUTS: {
                CONF_FORECAST: 5.0,
            },
            SECTION_PRICING: {
                CONF_PRICE_PRODUCTION: 0.0,
            },
            SECTION_ADVANCED: {
                CONF_CURTAILMENT: False,
            },
        },
    },
    {
        "description": "Curtailable solar with production price",
        "config": {
            SECTION_BASIC: {
                CONF_NAME: "Rooftop Solar",
                CONF_CONNECTION: "main_bus",
            },
            SECTION_INPUTS: {
                CONF_FORECAST: ["sensor.solar_power"],
            },
            SECTION_PRICING: {
                CONF_PRICE_PRODUCTION: 0.04,
            },
            SECTION_ADVANCED: {
                CONF_CURTAILMENT: True,
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
