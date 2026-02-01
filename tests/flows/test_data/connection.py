"""Test data and validation for connection flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.connection import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_SOURCE,
    CONF_TARGET,
    SECTION_ADVANCED,
    SECTION_BASIC,
    SECTION_ENDPOINTS,
    SECTION_LIMITS,
    SECTION_PRICING,
)

# Test data for connection flow - single-step with choose selector
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Basic connection configuration (no optional fields)",
        "config": {
            SECTION_BASIC: {
                CONF_NAME: "Battery to Grid",
            },
            SECTION_ENDPOINTS: {
                CONF_SOURCE: "Battery1",
                CONF_TARGET: "Grid1",
            },
            SECTION_LIMITS: {},
            SECTION_PRICING: {},
            SECTION_ADVANCED: {},
        },
    },
    {
        "description": "Connection with power limits and efficiency",
        "config": {
            SECTION_BASIC: {
                CONF_NAME: "Battery to Grid",
            },
            SECTION_ENDPOINTS: {
                CONF_SOURCE: "Battery1",
                CONF_TARGET: "Grid1",
            },
            SECTION_LIMITS: {
                CONF_MAX_POWER_SOURCE_TARGET: 10.0,
                CONF_MAX_POWER_TARGET_SOURCE: 10.0,
            },
            SECTION_PRICING: {},
            SECTION_ADVANCED: {
                CONF_EFFICIENCY_SOURCE_TARGET: 95.0,
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
