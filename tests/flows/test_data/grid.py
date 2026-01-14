"""Test grid config flow data for choose selector approach."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.grid import (
    CONF_CONNECTION,
    CONF_EXPORT_LIMIT,
    CONF_EXPORT_PRICE,
    CONF_IMPORT_LIMIT,
    CONF_IMPORT_PRICE,
)

# Test data for grid flow - single-step with choose selector
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Basic grid with all constant values",
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
