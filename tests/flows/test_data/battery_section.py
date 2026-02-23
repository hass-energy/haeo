"""Test data and validation for battery_section flow configuration."""

from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.schema import as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements.battery_section import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE,
    SECTION_COMMON,
    SECTION_STORAGE,
)

# Test data for battery_section flow - single-step with choose selector
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Battery section with sensor entities",
        "config": {
            SECTION_COMMON: {
                CONF_NAME: "Test Section",
            },
            SECTION_STORAGE: {
                CONF_CAPACITY: as_entity_value(["sensor.battery_capacity"]),
                CONF_INITIAL_CHARGE: as_entity_value(["sensor.battery_charge"]),
            },
        },
    },
    {
        "description": "Battery section with constant values",
        "config": {
            SECTION_COMMON: {
                CONF_NAME: "Constant Section",
            },
            SECTION_STORAGE: {
                CONF_CAPACITY: as_constant_value(10.0),
                CONF_INITIAL_CHARGE: as_constant_value(5.0),
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
