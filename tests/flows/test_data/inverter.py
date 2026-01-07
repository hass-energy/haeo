"""Test inverter config flow data for entity-first approach."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.inverter import (
    CONF_CONNECTION,
    CONF_EFFICIENCY_AC_TO_DC,
    CONF_EFFICIENCY_DC_TO_AC,
    CONF_MAX_POWER_AC_TO_DC,
    CONF_MAX_POWER_DC_TO_AC,
)

# Test data for inverter flow - entity-first approach
# Step 1 (mode_input): Select entities (including constant entities) for each field
# Step 2 (config): Enter constant values for fields with constant entities selected
VALID_DATA = [
    {
        "description": "Basic inverter with all constant values",
        "mode_input": {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "main_bus",
            CONF_MAX_POWER_DC_TO_AC: ["sensor.haeo_constant_power"],
            CONF_MAX_POWER_AC_TO_DC: ["sensor.haeo_constant_power"],
            CONF_EFFICIENCY_DC_TO_AC: ["sensor.haeo_constant_percentage"],
            CONF_EFFICIENCY_AC_TO_DC: ["sensor.haeo_constant_percentage"],
        },
        "config": {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "main_bus",
            CONF_MAX_POWER_DC_TO_AC: 5.0,
            CONF_MAX_POWER_AC_TO_DC: 5.0,
            CONF_EFFICIENCY_DC_TO_AC: 95.0,
            CONF_EFFICIENCY_AC_TO_DC: 95.0,
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
