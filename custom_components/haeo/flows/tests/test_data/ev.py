"""Test EV config flow data for choose selector approach."""

from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements.ev import (
    CONF_CAPACITY,
    CONF_CONNECTED,
    CONF_CURRENT_SOC,
    CONF_ENERGY_PER_DISTANCE,
    CONF_MAX_CHARGE_RATE,
    CONF_MAX_DISCHARGE_RATE,
    CONF_PUBLIC_CHARGING_PRICE,
    SECTION_CHARGING,
    SECTION_PUBLIC_CHARGING,
    SECTION_TRIP,
    SECTION_VEHICLE,
)
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
)

VALID_DATA = [
    {
        "description": "Basic EV with charge rate and public charging price",
        "config": {
            CONF_NAME: "Test EV",
            CONF_CONNECTION: as_connection_target("switchboard"),
            SECTION_VEHICLE: {
                CONF_CAPACITY: as_constant_value(60.0),
                CONF_ENERGY_PER_DISTANCE: as_constant_value(0.15),
                CONF_CURRENT_SOC: as_entity_value(["sensor.ev_soc"]),
            },
            SECTION_CHARGING: {
                CONF_MAX_CHARGE_RATE: as_constant_value(7.4),
                CONF_MAX_DISCHARGE_RATE: as_constant_value(5.0),
            },
            SECTION_TRIP: {
                CONF_CONNECTED: as_constant_value(1.0),
            },
            SECTION_PUBLIC_CHARGING: {
                CONF_PUBLIC_CHARGING_PRICE: as_constant_value(0.35),
            },
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(10.0),
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(10.0),
            },
            SECTION_EFFICIENCY: {
                CONF_EFFICIENCY_SOURCE_TARGET: as_constant_value(95.0),
                CONF_EFFICIENCY_TARGET_SOURCE: as_constant_value(95.0),
            },
        },
    },
    {
        "description": "Minimal EV - charge only, no V2G",
        "config": {
            CONF_NAME: "Commuter EV",
            CONF_CONNECTION: as_connection_target("switchboard"),
            SECTION_VEHICLE: {
                CONF_CAPACITY: as_constant_value(40.0),
                CONF_ENERGY_PER_DISTANCE: as_constant_value(0.18),
                CONF_CURRENT_SOC: as_entity_value(["sensor.car_soc"]),
            },
            SECTION_CHARGING: {
                CONF_MAX_CHARGE_RATE: as_constant_value(3.6),
            },
            SECTION_PUBLIC_CHARGING: {},
            SECTION_POWER_LIMITS: {},
            SECTION_EFFICIENCY: {},
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
