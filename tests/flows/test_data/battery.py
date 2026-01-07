"""Test battery config flow."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.battery import (
    CONF_CAPACITY,
    CONF_CONNECTION,
    CONF_DISCHARGE_COST,
    CONF_EARLY_CHARGE_INCENTIVE,
    CONF_EFFICIENCY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_POWER,
    CONF_MAX_DISCHARGE_POWER,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_OVERCHARGE_COST,
    CONF_OVERCHARGE_PERCENTAGE,
    CONF_UNDERCHARGE_COST,
    CONF_UNDERCHARGE_PERCENTAGE,
)

# Test data for battery flow - entity-first approach
# Step 1 (mode_input): Select entities (including constant entities) for each field
# Step 2 (config): Enter constant values for fields with constant entities selected
VALID_DATA = [
    {
        "description": "Basic battery configuration",
        "mode_input": {
            CONF_NAME: "Test Battery",
            CONF_CONNECTION: "main_bus",
            CONF_CAPACITY: ["sensor.haeo_constant_energy"],
            CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
            CONF_MIN_CHARGE_PERCENTAGE: ["sensor.haeo_constant_percentage"],
            CONF_MAX_CHARGE_PERCENTAGE: ["sensor.haeo_constant_percentage"],
            CONF_EFFICIENCY: ["sensor.haeo_constant_percentage"],
            CONF_MAX_CHARGE_POWER: ["sensor.haeo_constant_power"],
            CONF_MAX_DISCHARGE_POWER: ["sensor.haeo_constant_power"],
            CONF_EARLY_CHARGE_INCENTIVE: ["sensor.haeo_constant_monetary"],
            CONF_DISCHARGE_COST: [],
            CONF_UNDERCHARGE_PERCENTAGE: [],
            CONF_OVERCHARGE_PERCENTAGE: [],
            CONF_UNDERCHARGE_COST: [],
            CONF_OVERCHARGE_COST: [],
        },
        "config": {
            CONF_NAME: "Test Battery",
            CONF_CONNECTION: "main_bus",
            CONF_CAPACITY: 10.0,
            CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
            CONF_MAX_CHARGE_POWER: 5.0,
            CONF_MAX_DISCHARGE_POWER: 5.0,
        },
    },
    {
        "description": "Advanced battery configuration with efficiency and limits",
        "mode_input": {
            CONF_NAME: "Advanced Battery",
            CONF_CONNECTION: "main_bus",
            CONF_CAPACITY: ["sensor.haeo_constant_energy"],
            CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
            CONF_MIN_CHARGE_PERCENTAGE: ["sensor.haeo_constant_percentage"],
            CONF_MAX_CHARGE_PERCENTAGE: ["sensor.haeo_constant_percentage"],
            CONF_EFFICIENCY: ["sensor.haeo_constant_percentage"],
            CONF_MAX_CHARGE_POWER: ["sensor.haeo_constant_power"],
            CONF_MAX_DISCHARGE_POWER: ["sensor.haeo_constant_power"],
            CONF_EARLY_CHARGE_INCENTIVE: ["sensor.haeo_constant_monetary"],
            CONF_DISCHARGE_COST: ["sensor.haeo_constant_monetary"],
            CONF_UNDERCHARGE_PERCENTAGE: ["sensor.haeo_constant_percentage"],
            CONF_OVERCHARGE_PERCENTAGE: ["sensor.haeo_constant_percentage"],
            CONF_UNDERCHARGE_COST: ["sensor.haeo_constant_monetary"],
            CONF_OVERCHARGE_COST: ["sensor.haeo_constant_monetary"],
        },
        "config": {
            CONF_NAME: "Advanced Battery",
            CONF_CONNECTION: "main_bus",
            CONF_CAPACITY: 10.0,
            CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
            CONF_MIN_CHARGE_PERCENTAGE: 10.0,
            CONF_MAX_CHARGE_PERCENTAGE: 90.0,
            CONF_MAX_CHARGE_POWER: 5.0,
            CONF_MAX_DISCHARGE_POWER: 5.0,
            CONF_EFFICIENCY: 95.0,
            CONF_EARLY_CHARGE_INCENTIVE: 0.05,
            CONF_DISCHARGE_COST: 0.03,
            CONF_UNDERCHARGE_PERCENTAGE: 5.0,
            CONF_OVERCHARGE_PERCENTAGE: 95.0,
            CONF_UNDERCHARGE_COST: 0.10,
            CONF_OVERCHARGE_COST: 0.10,
        },
    },
]

# INVALID_DATA cases are handled by test_element_flow_user_step_missing_name
# in test_element_flows.py. Schema validation for constant values happens in step 2.
INVALID_DATA: list[dict[str, object]] = []
