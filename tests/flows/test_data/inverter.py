"""Test data and validation for inverter flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.inverter import (
    CONF_EFFICIENCY_AC_TO_DC,
    CONF_EFFICIENCY_DC_TO_AC,
    CONF_MAX_POWER_AC_TO_DC,
    CONF_MAX_POWER_DC_TO_AC,
)

# Test data for inverter flow
VALID_DATA = [
    {
        "description": "Basic inverter configuration",
        "config": {CONF_NAME: "Test Inverter"},
    },
    {
        "description": "Inverter with efficiency and power limits",
        "config": {
            CONF_NAME: "Hybrid Inverter",
            CONF_EFFICIENCY_DC_TO_AC: ["sensor.inverter_efficiency"],
            CONF_EFFICIENCY_AC_TO_DC: ["sensor.inverter_efficiency"],
            CONF_MAX_POWER_DC_TO_AC: ["sensor.inverter_max_power"],
            CONF_MAX_POWER_AC_TO_DC: ["sensor.inverter_max_power"],
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {CONF_NAME: ""},
        "error": "cannot be empty",
    },
]
