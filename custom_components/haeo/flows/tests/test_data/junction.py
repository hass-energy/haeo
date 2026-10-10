"""Test data and validation for junction flow configuration."""

from custom_components.haeo.core.const import CONF_NAME

# Test data for junction flow
VALID_DATA = [
    {
        "description": "Basic junction configuration",
        "config": {CONF_NAME: "Test Junction"},
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {CONF_NAME: ""},
        "error": "cannot be empty",
    },
]
