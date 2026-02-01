"""Test data and validation for node flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.node import CONF_IS_SINK, CONF_IS_SOURCE, SECTION_ADVANCED, SECTION_DETAILS

# Test data for node flow
VALID_DATA = [
    {
        "description": "Basic node configuration",
        "config": {
            SECTION_DETAILS: {CONF_NAME: "Test Node"},
            SECTION_ADVANCED: {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {
            SECTION_DETAILS: {CONF_NAME: ""},
            SECTION_ADVANCED: {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
        },
        "error": "cannot be empty",
    },
]
