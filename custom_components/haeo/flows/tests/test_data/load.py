"""Test data and validation for load flow configuration."""

from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.core.schema.elements.load import (
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_CURTAILMENT,
    SECTION_FORECAST,
    SECTION_PRICING,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION

# Test data for load flow - single-step with choose selector
# config: Contains all field values in choose selector format
VALID_DATA = [
    {
        "description": "Load with forecast sensors (variable load)",
        "config": {
            CONF_NAME: "Test Load",
            CONF_CONNECTION: as_connection_target("main_bus"),
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
            CONF_NAME: "Constant Load",
            CONF_CONNECTION: as_connection_target("main_bus"),
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
