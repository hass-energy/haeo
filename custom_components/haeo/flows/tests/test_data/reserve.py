"""Test data and validation for reserve flow configuration."""

from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.schema import as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements.reserve import (
    CONF_GENERATION,
    CONF_LOADS,
    CONF_MINIMUM,
    CONF_SHORTFALL_COST,
    CONF_STORAGE,
    CONF_WINDOW,
    SECTION_PARTICIPANTS,
    SECTION_PRICING,
    SECTION_REQUIREMENT,
)

VALID_DATA = [
    {
        "description": "Reserve covering a load less solar",
        "config": {
            CONF_NAME: "Backup Reserve",
            SECTION_PARTICIPANTS: {
                CONF_LOADS: ["House"],
                CONF_GENERATION: ["Solar"],
                CONF_STORAGE: ["Battery"],
            },
            SECTION_REQUIREMENT: {
                CONF_WINDOW: as_constant_value(12.0),
                CONF_MINIMUM: as_constant_value(2.0),
            },
            SECTION_PRICING: {
                CONF_SHORTFALL_COST: as_constant_value(0.05),
            },
        },
    },
    {
        "description": "Reserve holding a sensor-driven extra amount only",
        "config": {
            CONF_NAME: "Storm Reserve",
            SECTION_PARTICIPANTS: {CONF_STORAGE: ["Battery"]},
            SECTION_REQUIREMENT: {
                CONF_WINDOW: as_constant_value(4.0),
                CONF_MINIMUM: as_entity_value(["sensor.storm_reserve"]),
            },
            SECTION_PRICING: {
                CONF_SHORTFALL_COST: as_constant_value(1.0),
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
