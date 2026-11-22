"""Test data and validation for connection flow configuration."""

from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.schema import as_connection_target, as_constant_value
from custom_components.haeo.core.schema.elements.connection import (
    CONF_EFFICIENCY,
    CONF_MAX_POWER,
    CONF_SEGMENT_TYPE,
    CONF_SEGMENTS,
    CONF_SOURCE,
    CONF_TARGET,
    SECTION_ENDPOINTS,
)
from custom_components.haeo.flows.elements.connection import CONF_PATH

LIMIT_THEN_LOSSES = [
    {CONF_SEGMENT_TYPE: "power_limit", CONF_MAX_POWER: as_constant_value(10.0)},
    {CONF_SEGMENT_TYPE: "efficiency", CONF_EFFICIENCY: as_constant_value(95.0)},
]

# Each config is what the connection's subentry stores, and each user input what its form submits for it
VALID_DATA = [
    {
        "description": "Connection with no segments",
        "config": {
            CONF_NAME: "Battery to Grid",
            SECTION_ENDPOINTS: {
                CONF_SOURCE: as_connection_target("Battery1"),
                CONF_TARGET: as_connection_target("Grid1"),
            },
            CONF_SEGMENTS: [],
        },
        "user_input": {
            CONF_NAME: "Battery to Grid",
            CONF_PATH: {CONF_SOURCE: "Battery1", CONF_TARGET: "Grid1", CONF_SEGMENTS: []},
        },
    },
    {
        "description": "Connection with a limit, then losses",
        "config": {
            CONF_NAME: "Battery to Grid",
            SECTION_ENDPOINTS: {
                CONF_SOURCE: as_connection_target("Battery1"),
                CONF_TARGET: as_connection_target("Grid1"),
            },
            CONF_SEGMENTS: LIMIT_THEN_LOSSES,
        },
        "user_input": {
            CONF_NAME: "Battery to Grid",
            CONF_PATH: {CONF_SOURCE: "Battery1", CONF_TARGET: "Grid1", CONF_SEGMENTS: LIMIT_THEN_LOSSES},
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
