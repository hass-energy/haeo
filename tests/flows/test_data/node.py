"""Test data and validation for node flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.schema.elements.node import CONF_IS_SINK, CONF_IS_SOURCE, SECTION_COMMON, SECTION_ROLE

# Test data for node flow
VALID_DATA = [
    {
        "description": "Basic node configuration",
        "config": {
            SECTION_COMMON: {CONF_NAME: "Test Node"},
            SECTION_ROLE: {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {
            SECTION_COMMON: {CONF_NAME: ""},
            SECTION_ROLE: {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
        },
        "error": "cannot be empty",
    },
]
