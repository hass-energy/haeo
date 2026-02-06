"""Test grid config flow data for choose selector approach."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.grid import (
    CONF_CONNECTION,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_DEMAND_PRICING,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)
from custom_components.haeo.schema import as_connection_target, as_constant_value

# Test data for grid flow - single-step with choose selector
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Basic grid with all constant values",
        "config": {
            SECTION_COMMON: {
                CONF_NAME: "Test Grid",
                CONF_CONNECTION: as_connection_target("main_bus"),
            },
            SECTION_PRICING: {
                CONF_PRICE_SOURCE_TARGET: as_constant_value(0.30),
                CONF_PRICE_TARGET_SOURCE: as_constant_value(0.05),
            },
            SECTION_DEMAND_PRICING: {},
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(10.0),
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(10.0),
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
