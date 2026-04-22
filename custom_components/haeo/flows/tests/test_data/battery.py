"""Test battery config flow data for choose selector approach."""

from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_SALVAGE_VALUE,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
    SECTION_STORAGE,
)
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
)

# Test data for battery flow - single-step with choose selector
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Basic battery configuration",
        "config": {
            CONF_NAME: "Test Battery",
            CONF_CONNECTION: as_connection_target("main_bus"),
            SECTION_STORAGE: {
                CONF_CAPACITY: as_constant_value(10.0),
                CONF_INITIAL_CHARGE_PERCENTAGE: as_entity_value(["sensor.battery_soc"]),
            },
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
                CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(5.0),
            },
            SECTION_PRICING: {
                CONF_SALVAGE_VALUE: as_constant_value(0.0),
            },
            SECTION_EFFICIENCY: {
                CONF_EFFICIENCY_SOURCE_TARGET: as_constant_value(95.0),
                CONF_EFFICIENCY_TARGET_SOURCE: as_constant_value(95.0),
            },
        },
    },
    {
        "description": "Battery with salvage value",
        "config": {
            CONF_NAME: "Advanced Battery",
            CONF_CONNECTION: as_connection_target("main_bus"),
            SECTION_STORAGE: {
                CONF_CAPACITY: as_constant_value(10.0),
                CONF_INITIAL_CHARGE_PERCENTAGE: as_entity_value(["sensor.battery_soc"]),
            },
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
                CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(5.0),
            },
            SECTION_PRICING: {
                CONF_SALVAGE_VALUE: as_constant_value(0.02),
            },
            SECTION_EFFICIENCY: {
                CONF_EFFICIENCY_SOURCE_TARGET: as_constant_value(95.0),
                CONF_EFFICIENCY_TARGET_SOURCE: as_constant_value(95.0),
            },
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {
            CONF_NAME: "",
            CONF_CONNECTION: as_connection_target("main_bus"),
            SECTION_STORAGE: {
                CONF_CAPACITY: as_constant_value(10.0),
                CONF_INITIAL_CHARGE_PERCENTAGE: as_entity_value(["sensor.battery_soc"]),
            },
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
                CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(5.0),
            },
            SECTION_PRICING: {
                CONF_SALVAGE_VALUE: as_constant_value(0.0),
            },
            SECTION_EFFICIENCY: {
                CONF_EFFICIENCY_SOURCE_TARGET: as_constant_value(95.0),
                CONF_EFFICIENCY_TARGET_SOURCE: as_constant_value(95.0),
            },
        },
        "error": "cannot be empty",
    },
]
