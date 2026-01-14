"""Test data and validation for battery_section flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.battery_section import CONF_CAPACITY, CONF_INITIAL_CHARGE

# Test data for battery_section flow - single-step with choose selector
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Battery section with sensor entities",
        "config": {
            CONF_NAME: "Test Section",
            CONF_CAPACITY: {"choice": "entity", "value": ["sensor.battery_capacity"]},
            CONF_INITIAL_CHARGE: {"choice": "entity", "value": ["sensor.battery_charge"]},
        },
    },
    {
        "description": "Battery section with constant values",
        "config": {
            CONF_NAME: "Constant Section",
            CONF_CAPACITY: {"choice": "constant", "value": 10.0},
            CONF_INITIAL_CHARGE: {"choice": "constant", "value": 5.0},
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
