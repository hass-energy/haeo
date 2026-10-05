"""Test deferrable load config flow data for choose selector approach."""

from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.schema import (
    as_calendar_value,
    as_connection_target,
    as_constant_value,
    as_entity_value,
)
from custom_components.haeo.core.schema.elements.deferrable_load import (
    CONF_DEFICIT_PRICE,
    CONF_ENERGY_DELIVERED,
    CONF_MAX_POWER,
    CONF_OVERAGE_PRICE,
    CONF_WINDOW_CALENDAR,
    SECTION_POWER,
    SECTION_PRICING,
    SECTION_SCHEDULE,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION

VALID_DATA = [
    {
        "description": "Pool pump with scheduled windows, delivered energy sensor, and power limit",
        "config": {
            CONF_NAME: "Pool Pump",
            CONF_CONNECTION: as_connection_target("switchboard"),
            SECTION_SCHEDULE: {
                CONF_WINDOW_CALENDAR: as_calendar_value("calendar.pool_pump"),
                CONF_ENERGY_DELIVERED: as_entity_value(["sensor.pool_pump_window_energy"]),
            },
            SECTION_PRICING: {
                CONF_DEFICIT_PRICE: as_constant_value(10.0),
                CONF_OVERAGE_PRICE: as_constant_value(0.1),
            },
            SECTION_POWER: {
                CONF_MAX_POWER: as_constant_value(1.5),
            },
        },
    },
    {
        "description": "Minimal deferrable load - calendar and shortfall price only",
        "config": {
            CONF_NAME: "Hot Water",
            CONF_CONNECTION: as_connection_target("switchboard"),
            SECTION_SCHEDULE: {
                CONF_WINDOW_CALENDAR: as_calendar_value("calendar.hot_water"),
            },
            SECTION_PRICING: {
                CONF_DEFICIT_PRICE: as_constant_value(10.0),
            },
            SECTION_POWER: {},
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
