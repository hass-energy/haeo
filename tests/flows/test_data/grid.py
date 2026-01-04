"""Test grid config flow data for entity-first approach."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.grid import (
    CONF_CONNECTION,
    CONF_EXPORT_LIMIT,
    CONF_EXPORT_PRICE,
    CONF_IMPORT_LIMIT,
    CONF_IMPORT_PRICE,
)

# Test data for grid flow - entity-first approach
# Step 1 (mode_input): Select entities (including constant entities) for each field
# Step 2 (config): Enter constant values for fields with constant entities selected
VALID_DATA = [
    {
        "description": "Basic grid with all constant values",
        "mode_input": {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "main_bus",
            CONF_IMPORT_PRICE: ["sensor.haeo_constant_monetary"],
            CONF_EXPORT_PRICE: ["sensor.haeo_constant_monetary"],
            CONF_IMPORT_LIMIT: ["sensor.haeo_constant_power"],
            CONF_EXPORT_LIMIT: ["sensor.haeo_constant_power"],
        },
        "config": {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "main_bus",
            CONF_IMPORT_PRICE: 0.30,
            CONF_EXPORT_PRICE: 0.05,
            CONF_IMPORT_LIMIT: 10.0,
            CONF_EXPORT_LIMIT: 10.0,
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
