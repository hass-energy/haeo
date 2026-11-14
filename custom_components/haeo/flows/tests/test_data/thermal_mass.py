"""Test data and validation for thermal mass flow configuration."""

from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.schema import as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements.thermal_mass import (
    CONF_AMBIENT_TEMPERATURE,
    CONF_COMFORT_COST,
    CONF_HEAT_CAPACITY,
    CONF_HEAT_LOSS,
    CONF_HIGHEST_TEMPERATURE,
    CONF_MAX_TEMPERATURE,
    CONF_MIN_TEMPERATURE,
    CONF_TEMPERATURE,
    SECTION_COMFORT,
    SECTION_STORAGE,
    SECTION_SURROUNDINGS,
)

VALID_DATA = [
    {
        "description": "Hot water tank in a cupboard",
        "config": {
            CONF_NAME: "Hot Water",
            SECTION_STORAGE: {
                CONF_HEAT_CAPACITY: as_constant_value(0.29),
                CONF_TEMPERATURE: as_entity_value(["sensor.tank_temperature"]),
                CONF_HIGHEST_TEMPERATURE: as_constant_value(65.0),
            },
            SECTION_COMFORT: {
                CONF_MIN_TEMPERATURE: as_constant_value(45.0),
                CONF_COMFORT_COST: as_constant_value(1.0),
            },
            SECTION_SURROUNDINGS: {
                CONF_AMBIENT_TEMPERATURE: as_constant_value(20.0),
                CONF_HEAT_LOSS: as_constant_value(0.002),
            },
        },
    },
    {
        "description": "Room with a comfort band",
        "config": {
            CONF_NAME: "Lounge",
            SECTION_STORAGE: {
                CONF_HEAT_CAPACITY: as_constant_value(2.0),
                CONF_TEMPERATURE: as_entity_value(["sensor.lounge_temperature"]),
            },
            SECTION_COMFORT: {
                CONF_MIN_TEMPERATURE: as_constant_value(20.0),
                CONF_MAX_TEMPERATURE: as_constant_value(24.0),
                CONF_COMFORT_COST: as_constant_value(0.5),
            },
            SECTION_SURROUNDINGS: {
                CONF_AMBIENT_TEMPERATURE: as_entity_value(["sensor.outdoor_temperature"]),
                CONF_HEAT_LOSS: as_constant_value(0.15),
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
