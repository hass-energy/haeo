"""Test data and validation for solar flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.schema.elements.solar import (
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_SOURCE_TARGET,
    SECTION_COMMON,
    SECTION_CURTAILMENT,
    SECTION_FORECAST,
    SECTION_PRICING,
)

# Test data for solar flow - single-step with choose selector
# config: Contains all field values in choose selector format
# Note: price_source_target and curtailment have force_required=True, so they must be included
VALID_DATA = [
    {
        "description": "Basic solar configuration with constant forecast",
        "config": {
            SECTION_COMMON: {
                CONF_NAME: "Test Solar",
                CONF_CONNECTION: as_connection_target("main_bus"),
            },
            SECTION_FORECAST: {
                CONF_FORECAST: as_constant_value(5.0),
            },
            SECTION_PRICING: {
                CONF_PRICE_SOURCE_TARGET: as_constant_value(0.0),
            },
            SECTION_CURTAILMENT: {
                CONF_CURTAILMENT: as_constant_value(value=False),
            },
        },
    },
    {
        "description": "Curtailable solar with production price",
        "config": {
            SECTION_COMMON: {
                CONF_NAME: "Rooftop Solar",
                CONF_CONNECTION: as_connection_target("main_bus"),
            },
            SECTION_FORECAST: {
                CONF_FORECAST: as_entity_value(["sensor.solar_power"]),
            },
            SECTION_PRICING: {
                CONF_PRICE_SOURCE_TARGET: as_constant_value(0.04),
            },
            SECTION_CURTAILMENT: {
                CONF_CURTAILMENT: as_constant_value(value=True),
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
