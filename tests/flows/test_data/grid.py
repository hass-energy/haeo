"""Test data and validation for grid flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.grid import (
    CONF_CONNECTION,
    CONF_EXPORT_LIMIT,
    CONF_EXPORT_PRICE,
    CONF_IMPORT_LIMIT,
    CONF_IMPORT_PRICE,
)
from custom_components.haeo.flows.field_schema import MODE_SUFFIX, InputMode

# Test data for grid flow
VALID_DATA = [
    {
        "description": "Basic grid configuration",
        "mode_input": {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "main_bus",
            f"{CONF_IMPORT_PRICE}{MODE_SUFFIX}": InputMode.ENTITY_LINK,
            f"{CONF_EXPORT_PRICE}{MODE_SUFFIX}": InputMode.ENTITY_LINK,
            f"{CONF_IMPORT_LIMIT}{MODE_SUFFIX}": InputMode.CONSTANT,
            f"{CONF_EXPORT_LIMIT}{MODE_SUFFIX}": InputMode.CONSTANT,
        },
        "config": {
            CONF_NAME: "Test Grid",
            CONF_IMPORT_LIMIT: 5000,
            CONF_EXPORT_LIMIT: 3000,
            CONF_IMPORT_PRICE: ["sensor.grid_import_price"],
            CONF_EXPORT_PRICE: ["sensor.grid_export_price"],
        },
    },
    {
        "description": "Grid with sensor-based pricing",
        "mode_input": {
            CONF_NAME: "Smart Grid",
            CONF_CONNECTION: "main_bus",
            f"{CONF_IMPORT_PRICE}{MODE_SUFFIX}": InputMode.ENTITY_LINK,
            f"{CONF_EXPORT_PRICE}{MODE_SUFFIX}": InputMode.ENTITY_LINK,
            f"{CONF_IMPORT_LIMIT}{MODE_SUFFIX}": InputMode.CONSTANT,
            f"{CONF_EXPORT_LIMIT}{MODE_SUFFIX}": InputMode.CONSTANT,
        },
        "config": {
            CONF_NAME: "Smart Grid",
            CONF_IMPORT_LIMIT: 8000,
            CONF_EXPORT_LIMIT: 5000,
            CONF_IMPORT_PRICE: ["sensor.smart_grid_import_price"],
            CONF_EXPORT_PRICE: ["sensor.smart_grid_export_price"],
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {
            CONF_NAME: "",
            CONF_IMPORT_LIMIT: 5000,
            CONF_IMPORT_PRICE: ["sensor.grid_import_price"],
            CONF_EXPORT_PRICE: ["sensor.grid_export_price"],
        },
        "error": "cannot be empty",
    },
    {
        "description": "Negative import limit should fail validation",
        "config": {
            CONF_NAME: "Test Grid",
            CONF_IMPORT_LIMIT: -1000,
            CONF_IMPORT_PRICE: ["sensor.grid_import_price"],
            CONF_EXPORT_PRICE: ["sensor.grid_export_price"],
        },
        "error": "value must be positive",
    },
]
