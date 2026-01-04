"""Test battery config flow data for entity-first approach."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.battery import (
    CONF_CAPACITY,
    CONF_CONNECTION,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_POWER,
    CONF_MAX_DISCHARGE_POWER,
)

# Test data for battery flow - entity-first approach
# Step 1 (mode_input): Select entities (including constant entities) for each field
# Step 2 (config): Enter constant values for fields with constant entities selected
VALID_DATA = [
    {
        "description": "Basic battery with all constant values",
        "mode_input": {
            CONF_NAME: "Test Battery",
            CONF_CONNECTION: "main_bus",
            CONF_CAPACITY: ["sensor.haeo_constant_energy_storage"],
            CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.haeo_constant_battery"],
            CONF_MAX_CHARGE_POWER: ["sensor.haeo_constant_power"],
            CONF_MAX_DISCHARGE_POWER: ["sensor.haeo_constant_power"],
        },
        "config": {
            CONF_NAME: "Test Battery",
            CONF_CONNECTION: "main_bus",
            CONF_CAPACITY: 10.0,
            CONF_INITIAL_CHARGE_PERCENTAGE: 50.0,
            CONF_MAX_CHARGE_POWER: 5.0,
            CONF_MAX_DISCHARGE_POWER: 5.0,
        },
    },
]

INVALID_DATA: list[dict[str, object]] = []
