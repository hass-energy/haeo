"""Test inverter config flow data for choose selector approach."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.inverter import (
    CONF_CONNECTION,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
)
from custom_components.haeo.schema import as_connection_target, as_constant_value

# Test data for inverter flow - single-step with choose selector
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Basic inverter with all constant values",
        "config": {
            SECTION_COMMON: {
                CONF_NAME: "Test Inverter",
                CONF_CONNECTION: as_connection_target("main_bus"),
            },
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(5.0),
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
            },
            SECTION_EFFICIENCY: {
                CONF_EFFICIENCY_SOURCE_TARGET: as_constant_value(95.0),
                CONF_EFFICIENCY_TARGET_SOURCE: as_constant_value(95.0),
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
