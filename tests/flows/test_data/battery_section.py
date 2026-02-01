"""Test data and validation for battery_section flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.battery_section import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE,
    SECTION_BASIC,
    SECTION_STORAGE,
)

# Test data for battery_section flow - single-step with choose selector
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Battery section with sensor entities",
        "config": {
            SECTION_BASIC: {
                CONF_NAME: "Test Section",
            },
            SECTION_STORAGE: {
                CONF_CAPACITY: ["sensor.battery_capacity"],
                CONF_INITIAL_CHARGE: ["sensor.battery_charge"],
            },
        },
    },
    {
        "description": "Battery section with constant values",
        "config": {
            SECTION_BASIC: {
                CONF_NAME: "Constant Section",
            },
            SECTION_STORAGE: {
                CONF_CAPACITY: 10.0,
                CONF_INITIAL_CHARGE: 5.0,
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
