"""Test data and validation for load flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.load import (
    CONF_CONNECTION,
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_CURTAILMENT,
    SECTION_FORECAST,
    SECTION_PRICING,
)
from custom_components.haeo.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value

# Test data for load flow - single-step with choose selector
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Load with forecast sensors (variable load)",
        "config": {
            SECTION_COMMON: {
                CONF_NAME: "Test Load",
                CONF_CONNECTION: as_connection_target("main_bus"),
            },
            SECTION_FORECAST: {
                CONF_FORECAST: as_entity_value(["sensor.forecast1", "sensor.forecast2"]),
            },
            SECTION_PRICING: {
                CONF_PRICE_TARGET_SOURCE: as_none_value(),
            },
            SECTION_CURTAILMENT: {
                CONF_CURTAILMENT: as_constant_value(value=False),
            },
        },
    },
    {
        "description": "Load with constant value (fixed load pattern)",
        "config": {
            SECTION_COMMON: {
                CONF_NAME: "Constant Load",
                CONF_CONNECTION: as_connection_target("main_bus"),
            },
            SECTION_FORECAST: {
                CONF_FORECAST: as_constant_value(1.5),
            },
            SECTION_PRICING: {
                CONF_PRICE_TARGET_SOURCE: as_none_value(),
            },
            SECTION_CURTAILMENT: {
                CONF_CURTAILMENT: as_constant_value(value=False),
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
