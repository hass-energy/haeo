"""Test data and validation for node flow configuration."""

from custom_components.haeo.const import CONF_NAME

# Test data for node flow
VALID_DATA = [
    {
        "description": "Basic node configuration",
        "config": {CONF_NAME: "Test Node"},
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {CONF_NAME: ""},
        "error": "cannot be empty",
    },
]
