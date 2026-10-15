"""Test data and validation for buffer flow configuration."""

from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.schema import as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.core.schema.elements.buffer import (
    CONF_GENERATION,
    CONF_KIND,
    CONF_LEVEL,
    CONF_LOADS,
    CONF_SHORTFALL_COST,
    CONF_STORAGE,
    CONF_WINDOW,
    KIND_HEADROOM,
    KIND_RESERVE,
    SECTION_PARTICIPANTS,
    SECTION_PRICING,
    SECTION_REQUIREMENT,
)

VALID_DATA = [
    {
        "description": "Reserve covering a load less solar above a fixed level",
        "config": {
            CONF_NAME: "Backup Reserve",
            CONF_KIND: KIND_RESERVE,
            SECTION_PARTICIPANTS: {
                CONF_LOADS: ["House"],
                CONF_GENERATION: ["Solar"],
                CONF_STORAGE: ["Battery"],
            },
            SECTION_REQUIREMENT: {
                CONF_WINDOW: as_constant_value(12.0),
                CONF_LEVEL: as_constant_value(20.0),
            },
            SECTION_PRICING: {
                CONF_SHORTFALL_COST: as_constant_value(0.05),
            },
        },
    },
    {
        "description": "Headroom for solar less the house above a sensor-driven level",
        "config": {
            CONF_NAME: "Solar Headroom",
            CONF_KIND: KIND_HEADROOM,
            SECTION_PARTICIPANTS: {
                CONF_LOADS: ["House"],
                CONF_GENERATION: ["Solar"],
                CONF_STORAGE: ["Battery"],
            },
            SECTION_REQUIREMENT: {
                CONF_WINDOW: as_constant_value(8.0),
                CONF_LEVEL: as_entity_value(["sensor.headroom_level"]),
            },
            SECTION_PRICING: {
                CONF_SHORTFALL_COST: as_entity_value(["sensor.shortfall_cost"]),
            },
        },
    },
    {
        "description": "Reserve measured from the battery's own minimum charge",
        "config": {
            CONF_NAME: "Storm Reserve",
            CONF_KIND: KIND_RESERVE,
            SECTION_PARTICIPANTS: {CONF_STORAGE: ["Battery"]},
            SECTION_REQUIREMENT: {
                CONF_WINDOW: as_constant_value(4.0),
                CONF_LEVEL: as_none_value(),
            },
            SECTION_PRICING: {
                CONF_SHORTFALL_COST: as_constant_value(1.0),
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
