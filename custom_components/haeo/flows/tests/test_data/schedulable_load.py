"""Test schedulable load config flow data for choose selector approach."""

from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements.schedulable_load import (
    CONF_DEFICIT_PRICE,
    CONF_DURATION,
    CONF_ENERGY_METER,
    CONF_INTEGER_MODE,
    CONF_POWER,
    CONF_RUNNING,
    CONF_WINDOW_CALENDAR,
    SECTION_ADVANCED,
    SECTION_PRICING,
    SECTION_PROFILE,
    SECTION_SCHEDULE,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION

VALID_DATA = [
    {
        "description": "Dishwasher with a running sensor, energy meter, and every start integer",
        "config": {
            CONF_NAME: "Dishwasher",
            CONF_CONNECTION: as_connection_target("switchboard"),
            SECTION_SCHEDULE: {
                CONF_WINDOW_CALENDAR: as_entity_value(["calendar.dishwasher"]),
                CONF_RUNNING: as_entity_value(["binary_sensor.dishwasher_running"]),
                CONF_ENERGY_METER: as_entity_value(["sensor.dishwasher_energy"]),
            },
            SECTION_PROFILE: {
                CONF_POWER: as_constant_value(1.8),
                CONF_DURATION: as_constant_value(2.5),
            },
            SECTION_PRICING: {
                CONF_DEFICIT_PRICE: as_constant_value(10.0),
            },
            SECTION_ADVANCED: {
                CONF_INTEGER_MODE: "all",
            },
        },
    },
    {
        "description": "Minimal schedulable load - calendar, profile, and missed run price",
        "config": {
            CONF_NAME: "Washing Machine",
            CONF_CONNECTION: as_connection_target("switchboard"),
            SECTION_SCHEDULE: {
                CONF_WINDOW_CALENDAR: as_entity_value(["calendar.washing_machine"]),
            },
            SECTION_PROFILE: {
                CONF_POWER: as_entity_value(["sensor.washing_machine_power"]),
                CONF_DURATION: as_constant_value(1.5),
            },
            SECTION_PRICING: {
                CONF_DEFICIT_PRICE: as_constant_value(10.0),
            },
            SECTION_ADVANCED: {
                CONF_INTEGER_MODE: "first",
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
