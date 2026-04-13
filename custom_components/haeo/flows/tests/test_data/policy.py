"""Test data and validation for policy flow configuration."""

from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements.policy import (
    CONF_PRICE_SOURCE_TARGET,
    CONF_SOURCE,
    CONF_TAG,
    CONF_TARGET,
    SECTION_ENDPOINTS,
    SECTION_TAG_PRICING,
)

VALID_DATA = [
    {
        "description": "Basic policy configuration",
        "config": {
            CONF_NAME: "Solar Export Policy",
            SECTION_ENDPOINTS: {
                CONF_SOURCE: as_connection_target("Solar"),
                CONF_TARGET: as_connection_target("Grid"),
            },
            SECTION_TAG_PRICING: {
                CONF_TAG: 1,
                CONF_PRICE_SOURCE_TARGET: 0.02,
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
