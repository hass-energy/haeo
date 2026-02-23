"""Test battery config flow data for choose selector approach."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_CONFIGURE_PARTITIONS,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    CONF_SALVAGE_VALUE,
    SECTION_COMMON,
    SECTION_EFFICIENCY,
    SECTION_LIMITS,
    SECTION_PARTITIONING,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
    SECTION_STORAGE,
)

# Test data for battery flow - single-step with choose selector (plus optional partition step)
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Basic battery configuration",
        "config": {
            SECTION_COMMON: {
                CONF_NAME: "Test Battery",
                CONF_CONNECTION: as_connection_target("main_bus"),
            },
            SECTION_STORAGE: {
                CONF_CAPACITY: as_constant_value(10.0),
                CONF_INITIAL_CHARGE_PERCENTAGE: as_entity_value(["sensor.battery_soc"]),
            },
            SECTION_LIMITS: {
                CONF_MIN_CHARGE_PERCENTAGE: as_constant_value(10.0),
                CONF_MAX_CHARGE_PERCENTAGE: as_constant_value(90.0),
            },
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
                CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(5.0),
            },
            SECTION_PRICING: {
                CONF_PRICE_TARGET_SOURCE: as_constant_value(0.01),
                CONF_SALVAGE_VALUE: as_constant_value(0.0),
            },
            SECTION_EFFICIENCY: {
                CONF_EFFICIENCY_SOURCE_TARGET: as_constant_value(95.0),
                CONF_EFFICIENCY_TARGET_SOURCE: as_constant_value(95.0),
            },
            SECTION_PARTITIONING: {
                CONF_CONFIGURE_PARTITIONS: False,
            },
        },
    },
    {
        "description": "Battery with optional discharge cost",
        "config": {
            SECTION_COMMON: {
                CONF_NAME: "Advanced Battery",
                CONF_CONNECTION: as_connection_target("main_bus"),
            },
            SECTION_STORAGE: {
                CONF_CAPACITY: as_constant_value(10.0),
                CONF_INITIAL_CHARGE_PERCENTAGE: as_entity_value(["sensor.battery_soc"]),
            },
            SECTION_LIMITS: {
                CONF_MIN_CHARGE_PERCENTAGE: as_constant_value(10.0),
                CONF_MAX_CHARGE_PERCENTAGE: as_constant_value(90.0),
            },
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
                CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(5.0),
            },
            SECTION_PRICING: {
                CONF_PRICE_TARGET_SOURCE: as_constant_value(0.05),
                CONF_PRICE_SOURCE_TARGET: as_constant_value(0.03),
                CONF_SALVAGE_VALUE: as_constant_value(0.02),
            },
            SECTION_EFFICIENCY: {
                CONF_EFFICIENCY_SOURCE_TARGET: as_constant_value(95.0),
                CONF_EFFICIENCY_TARGET_SOURCE: as_constant_value(95.0),
            },
            SECTION_PARTITIONING: {
                CONF_CONFIGURE_PARTITIONS: False,
            },
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {
            SECTION_COMMON: {
                CONF_NAME: "",
                CONF_CONNECTION: as_connection_target("main_bus"),
            },
            SECTION_STORAGE: {
                CONF_CAPACITY: as_constant_value(10.0),
                CONF_INITIAL_CHARGE_PERCENTAGE: as_entity_value(["sensor.battery_soc"]),
            },
            SECTION_LIMITS: {},
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
                CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(5.0),
            },
            SECTION_PRICING: {
                CONF_PRICE_TARGET_SOURCE: as_constant_value(0.01),
                CONF_SALVAGE_VALUE: as_constant_value(0.0),
            },
            SECTION_EFFICIENCY: {
                CONF_EFFICIENCY_SOURCE_TARGET: as_constant_value(95.0),
                CONF_EFFICIENCY_TARGET_SOURCE: as_constant_value(95.0),
            },
            SECTION_PARTITIONING: {
                CONF_CONFIGURE_PARTITIONS: False,
            },
        },
        "error": "cannot be empty",
    },
]
