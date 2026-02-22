"""Test data and validation for connection flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.schema import as_connection_target, as_constant_value
from custom_components.haeo.schema.elements.connection import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_SOURCE,
    CONF_TARGET,
    SECTION_COMMON,
    SECTION_EFFICIENCY,
    SECTION_ENDPOINTS,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)

# Test data for connection flow - single-step with choose selector
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Basic connection configuration (no optional fields)",
        "config": {
            SECTION_COMMON: {
                CONF_NAME: "Battery to Grid",
            },
            SECTION_ENDPOINTS: {
                CONF_SOURCE: as_connection_target("Battery1"),
                CONF_TARGET: as_connection_target("Grid1"),
            },
            SECTION_POWER_LIMITS: {},
            SECTION_PRICING: {},
            SECTION_EFFICIENCY: {},
        },
    },
    {
        "description": "Connection with power limits and efficiency",
        "config": {
            SECTION_COMMON: {
                CONF_NAME: "Battery to Grid",
            },
            SECTION_ENDPOINTS: {
                CONF_SOURCE: as_connection_target("Battery1"),
                CONF_TARGET: as_connection_target("Grid1"),
            },
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(10.0),
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(10.0),
            },
            SECTION_PRICING: {},
            SECTION_EFFICIENCY: {
                CONF_EFFICIENCY_SOURCE_TARGET: as_constant_value(95.0),
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
