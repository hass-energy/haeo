"""Test data and validation for headroom flow configuration."""

from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.schema import as_constant_value
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
        "description": "Headroom for solar less the house",
        "config": {
            CONF_NAME: "Solar Headroom",
            SECTION_PARTICIPANTS: {
                CONF_LOADS: ["House"],
                CONF_GENERATION: ["Solar"],
                CONF_STORAGE: ["Battery"],
            },
            SECTION_REQUIREMENT: {
                CONF_WINDOW: as_constant_value(8.0),
                CONF_MINIMUM: as_constant_value(0.0),
            },
            SECTION_PRICING: {
                CONF_SHORTFALL_COST: as_constant_value(0.05),
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
