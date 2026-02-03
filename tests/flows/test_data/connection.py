"""Test data and validation for connection flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.connection import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_SECTION_ADVANCED,
    CONF_SECTION_BASIC,
    CONF_SECTION_LIMITS,
    CONF_SOURCE,
    CONF_TARGET,
)

# Test data for connection flow - single-step with choose selector
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Basic connection configuration (no optional fields)",
        "config": {
            CONF_SECTION_BASIC: {
                CONF_NAME: "Battery to Grid",
                CONF_SOURCE: "Battery1",
                CONF_TARGET: "Grid1",
            },
            CONF_SECTION_LIMITS: {},
            CONF_SECTION_ADVANCED: {},
        },
    },
    {
        "description": "Connection with power limits and efficiency",
        "config": {
            CONF_SECTION_BASIC: {
                CONF_NAME: "Battery to Grid",
                CONF_SOURCE: "Battery1",
                CONF_TARGET: "Grid1",
            },
            CONF_SECTION_LIMITS: {
                CONF_MAX_POWER_SOURCE_TARGET: 10.0,
                CONF_MAX_POWER_TARGET_SOURCE: 10.0,
            },
            CONF_SECTION_ADVANCED: {
                CONF_EFFICIENCY_SOURCE_TARGET: 95.0,
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
