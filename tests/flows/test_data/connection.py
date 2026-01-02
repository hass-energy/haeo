"""Test data and validation for connection flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.connection import (
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_SOURCE,
    CONF_TARGET,
)

# Test data for connection flow
VALID_DATA = [
    {
        "description": "Basic connection configuration",
        "config": {
            CONF_NAME: "Battery to Grid",
            CONF_SOURCE: "Battery1",
            CONF_TARGET: "Grid1",
        },
        "mode_input": {
            CONF_NAME: "Battery to Grid",
            CONF_SOURCE: "Battery1",
            CONF_TARGET: "Grid1",
        },
        "values_input": {},
    },
    {
        "description": "Connection with power limits",
        "config": {
            CONF_NAME: "Battery to Grid",
            CONF_SOURCE: "Battery1",
            CONF_TARGET: "Grid1",
            CONF_MAX_POWER_SOURCE_TARGET: ["sensor.power_limit"],
            CONF_MAX_POWER_TARGET_SOURCE: ["sensor.power_limit"],
        },
        "mode_input": {
            CONF_NAME: "Battery to Grid",
            CONF_SOURCE: "Battery1",
            CONF_TARGET: "Grid1",
            CONF_MAX_POWER_SOURCE_TARGET: ["sensor.power_limit"],
            CONF_MAX_POWER_TARGET_SOURCE: ["sensor.power_limit"],
        },
        "values_input": {},
    },
]

INVALID_DATA = [
    {
        "description": "Empty source should fail validation",
        "config": {CONF_NAME: "Test Connection", CONF_SOURCE: "", CONF_TARGET: "Grid1"},
        "error": "element name cannot be empty",
    },
    {
        "description": "Empty target should fail validation",
        "config": {CONF_NAME: "Test Connection", CONF_SOURCE: "Battery1", CONF_TARGET: ""},
        "error": "element name cannot be empty",
    },
]
