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
            CONF_IMPORT_PRICE: ["haeo.configurable_entity"],
            CONF_EXPORT_PRICE: ["haeo.configurable_entity"],
            CONF_IMPORT_LIMIT: ["haeo.configurable_entity"],
            CONF_EXPORT_LIMIT: ["haeo.configurable_entity"],
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
