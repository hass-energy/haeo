"""Test data and validation for solar flow configuration."""

from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements.solar import (
    CONF_CURTAILMENT,
    CONF_FORECAST,
    SECTION_CURTAILMENT,
    SECTION_FORECAST,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION

# Test data for solar flow - single-step with choose selector
# config: Contains all field values in choose selector format
# Note: curtailment has force_required=True, so it must be included
VALID_DATA = [
    {
        "description": "Basic solar configuration with constant forecast",
        "config": {
            CONF_NAME: "Test Solar",
            CONF_CONNECTION: as_connection_target("main_bus"),
            SECTION_FORECAST: {
                CONF_FORECAST: as_constant_value(5.0),
            },
            SECTION_CURTAILMENT: {
                CONF_CURTAILMENT: as_constant_value(value=False),
            },
        },
    },
    {
        "description": "Curtailable solar",
        "config": {
            CONF_NAME: "Rooftop Solar",
            CONF_CONNECTION: as_connection_target("main_bus"),
            SECTION_FORECAST: {
                CONF_FORECAST: as_entity_value(["sensor.solar_power"]),
            },
            SECTION_CURTAILMENT: {
                CONF_CURTAILMENT: as_constant_value(value=True),
            },
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
