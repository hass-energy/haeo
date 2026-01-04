"""Test data and validation for inverter flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.inverter import (
    CONF_CONNECTION,
    CONF_EFFICIENCY_AC_TO_DC,
    CONF_EFFICIENCY_DC_TO_AC,
    CONF_MAX_POWER_AC_TO_DC,
    CONF_MAX_POWER_DC_TO_AC,
)

# Test data for inverter flow
VALID_DATA = [
    {
        "description": "Basic inverter configuration",
        "config": {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "Switchboard",
            CONF_MAX_POWER_DC_TO_AC: ["sensor.inverter_max_power"],
            CONF_MAX_POWER_AC_TO_DC: ["sensor.inverter_max_power"],
        },
        "mode_input": {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "Switchboard",
            CONF_MAX_POWER_DC_TO_AC: ["sensor.inverter_max_power"],
            CONF_MAX_POWER_AC_TO_DC: ["sensor.inverter_max_power"],
        },
        "values_input": {},
    },
    {
        "description": "Inverter with efficiency",
        "config": {
            CONF_NAME: "Hybrid Inverter",
            CONF_CONNECTION: "Switchboard",
            CONF_MAX_POWER_DC_TO_AC: ["sensor.inverter_max_power"],
            CONF_MAX_POWER_AC_TO_DC: ["sensor.inverter_max_power"],
            CONF_EFFICIENCY_DC_TO_AC: 95.0,
            CONF_EFFICIENCY_AC_TO_DC: 95.0,
        },
        "mode_input": {
            CONF_NAME: "Hybrid Inverter",
            CONF_CONNECTION: "Switchboard",
            CONF_MAX_POWER_DC_TO_AC: ["sensor.inverter_max_power"],
            CONF_MAX_POWER_AC_TO_DC: ["sensor.inverter_max_power"],
            CONF_EFFICIENCY_DC_TO_AC: 95.0,
            CONF_EFFICIENCY_AC_TO_DC: 95.0,
        },
        "values_input": {},
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {
            CONF_NAME: "",
            CONF_CONNECTION: "Switchboard",
            CONF_MAX_POWER_DC_TO_AC: ["sensor.inverter_max_power"],
            CONF_MAX_POWER_AC_TO_DC: ["sensor.inverter_max_power"],
        },
        "error": "cannot be empty",
    },
]
