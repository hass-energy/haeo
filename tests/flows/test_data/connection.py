"""Test data and validation for connection flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.connection import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    CONF_SOURCE,
    CONF_TARGET,
)

# Test data for connection flow - entity-first approach
# Step 1 (mode_input): Select entities (including constant entities) for each field
# Step 2 (config): Enter constant values for fields with constant entities selected
VALID_DATA = [
    {
        "description": "Basic connection configuration (no optional fields)",
        "mode_input": {
            CONF_NAME: "Battery to Grid",
            CONF_SOURCE: "Battery1",
            CONF_TARGET: "Grid1",
            CONF_MAX_POWER_SOURCE_TARGET: [],
            CONF_MAX_POWER_TARGET_SOURCE: [],
            CONF_EFFICIENCY_SOURCE_TARGET: [],
            CONF_EFFICIENCY_TARGET_SOURCE: [],
            CONF_PRICE_SOURCE_TARGET: [],
            CONF_PRICE_TARGET_SOURCE: [],
        },
        "config": {
            CONF_NAME: "Battery to Grid",
            CONF_SOURCE: "Battery1",
            CONF_TARGET: "Grid1",
        },
    },
    {
        "description": "Connection with power limits and efficiency",
        "mode_input": {
            CONF_NAME: "Battery to Grid",
            CONF_SOURCE: "Battery1",
            CONF_TARGET: "Grid1",
            CONF_MAX_POWER_SOURCE_TARGET: ["haeo.configurable_entity"],
            CONF_MAX_POWER_TARGET_SOURCE: ["haeo.configurable_entity"],
            CONF_EFFICIENCY_SOURCE_TARGET: ["haeo.configurable_entity"],
            CONF_EFFICIENCY_TARGET_SOURCE: [],
            CONF_PRICE_SOURCE_TARGET: [],
            CONF_PRICE_TARGET_SOURCE: [],
        },
        "config": {
            CONF_NAME: "Battery to Grid",
            CONF_SOURCE: "Battery1",
            CONF_TARGET: "Grid1",
            CONF_MAX_POWER_SOURCE_TARGET: 10.0,
            CONF_MAX_POWER_TARGET_SOURCE: 10.0,
            CONF_EFFICIENCY_SOURCE_TARGET: 95.0,
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
