"""Test data and validation for constant load flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.constant_load import CONF_POWER

# Test data for load constant flow
VALID_DATA = [
    {
        "description": "Fixed load configuration",
        "config": {
            CONF_NAME: "Test Load",
            CONF_POWER: 1500,
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {CONF_NAME: "", CONF_POWER: 1500},
        "error": "cannot be empty",
    },
    {
        "description": "Negative power should fail validation",
        "config": {CONF_NAME: "Test Load", CONF_POWER: -500},
        "error": "value must be positive",
    },
]
