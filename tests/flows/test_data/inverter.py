"""Test inverter config flow data for choose selector approach."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.inverter import (
    CONF_CONNECTION,
    CONF_EFFICIENCY_AC_TO_DC,
    CONF_EFFICIENCY_DC_TO_AC,
    CONF_MAX_POWER_AC_TO_DC,
    CONF_MAX_POWER_DC_TO_AC,
)

# Test data for inverter flow - single-step with choose selector
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Basic inverter with all constant values",
        "config": {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: "main_bus",
            CONF_MAX_POWER_DC_TO_AC: {"choice": "constant", "value": 5.0},
            CONF_MAX_POWER_AC_TO_DC: {"choice": "constant", "value": 5.0},
            CONF_EFFICIENCY_DC_TO_AC: {"choice": "constant", "value": 95.0},
            CONF_EFFICIENCY_AC_TO_DC: {"choice": "constant", "value": 95.0},
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
