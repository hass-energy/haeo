"""Test data and validation for grid flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.grid import (
    CONF_EXPORT_LIMIT,
    CONF_EXPORT_PRICE,
    CONF_IMPORT_LIMIT,
    CONF_IMPORT_PRICE,
)

# Test data for grid flow
VALID_DATA = [
    {
        "description": "Basic grid configuration",
        "config": {
            CONF_NAME: "Test Grid",
            CONF_IMPORT_LIMIT: 5000,
            CONF_EXPORT_LIMIT: 3000,
            CONF_IMPORT_PRICE: {
                "live": [],
                "forecast": [],
            },
            CONF_EXPORT_PRICE: {
                "live": [],
                "forecast": [],
            },
        },
    },
    {
        "description": "Grid with sensor-based pricing",
        "config": {
            CONF_NAME: "Smart Grid",
            CONF_IMPORT_LIMIT: 8000,
            CONF_EXPORT_LIMIT: 5000,
            CONF_IMPORT_PRICE: {
                "live": ["sensor.smart_grid_import_price"],
                "forecast": ["sensor.smart_grid_import_price"],
            },
            CONF_EXPORT_PRICE: {
                "live": ["sensor.smart_grid_export_price"],
                "forecast": ["sensor.smart_grid_export_price"],
            },
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {
            CONF_NAME: "",
            CONF_IMPORT_LIMIT: 5000,
            CONF_IMPORT_PRICE: {
                "live": [],
                "forecast": [],
            },
            CONF_EXPORT_PRICE: {
                "live": [],
                "forecast": [],
            },
        },
        "error": "cannot be empty",
    },
    {
        "description": "Negative import limit should fail validation",
        "config": {
            CONF_NAME: "Test Grid",
            CONF_IMPORT_LIMIT: -1000,
            CONF_IMPORT_PRICE: {
                "live": [],
                "forecast": [],
            },
            CONF_EXPORT_PRICE: {
                "live": [],
                "forecast": [],
            },
        },
        "error": "value must be positive",
    },
]
