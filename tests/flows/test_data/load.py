"""Test data and validation for load flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.load import CONF_CONNECTION, CONF_FORECAST, SECTION_DETAILS, SECTION_FORECAST

# Test data for load flow - single-step with choose selector
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Load with forecast sensors (variable load)",
        "config": {
            SECTION_DETAILS: {
                CONF_NAME: "Test Load",
                CONF_CONNECTION: "main_bus",
            },
            SECTION_FORECAST: {
                CONF_FORECAST: ["sensor.forecast1", "sensor.forecast2"],
            },
        },
    },
    {
        "description": "Load with constant value (fixed load pattern)",
        "config": {
            SECTION_DETAILS: {
                CONF_NAME: "Constant Load",
                CONF_CONNECTION: "main_bus",
            },
            SECTION_FORECAST: {
                CONF_FORECAST: 1.5,
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
