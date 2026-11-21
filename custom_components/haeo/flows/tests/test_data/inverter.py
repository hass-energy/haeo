"""Test data and validation for inverter flow configuration."""

from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.schema import as_connection_target, as_constant_value
from custom_components.haeo.core.schema.elements.inverter import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION

# Each config is both what the inverter form submits and what its subentry stores
VALID_DATA = [
    {
        "description": "Basic inverter with all constant values",
        "config": {
            CONF_NAME: "Test Inverter",
            CONF_CONNECTION: as_connection_target("main_bus"),
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
