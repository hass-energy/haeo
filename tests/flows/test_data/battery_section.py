"""Test data and validation for battery_section flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.battery_section import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE,
    CONF_SECTION_BASIC,
    CONF_SECTION_INPUTS,
)

# Test data for battery_section flow - single-step with choose selector
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Battery section with sensor entities",
        "config": {
            CONF_SECTION_BASIC: {
                CONF_NAME: "Test Section",
            },
            CONF_SECTION_INPUTS: {
                CONF_CAPACITY: ["sensor.battery_capacity"],
                CONF_INITIAL_CHARGE: ["sensor.battery_charge"],
            },
        },
    },
    {
        "description": "Battery section with constant values",
        "config": {
            CONF_SECTION_BASIC: {
                CONF_NAME: "Constant Section",
            },
            CONF_SECTION_INPUTS: {
                CONF_CAPACITY: 10.0,
                CONF_INITIAL_CHARGE: 5.0,
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
