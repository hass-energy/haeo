"""Test inverter config flow data for choose selector approach."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.inverter import (
    CONF_CONNECTION,
    CONF_EFFICIENCY_AC_TO_DC,
    CONF_EFFICIENCY_DC_TO_AC,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    SECTION_ADVANCED,
    SECTION_COMMON,
    SECTION_POWER_LIMITS,
)

# Test data for inverter flow - single-step with choose selector
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Basic inverter with all constant values",
        "config": {
            SECTION_COMMON: {
                CONF_NAME: "Test Inverter",
                CONF_CONNECTION: "main_bus",
            },
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_SOURCE_TARGET: 5.0,
                CONF_MAX_POWER_TARGET_SOURCE: 5.0,
            },
            SECTION_ADVANCED: {
                CONF_EFFICIENCY_DC_TO_AC: 95.0,
                CONF_EFFICIENCY_AC_TO_DC: 95.0,
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
