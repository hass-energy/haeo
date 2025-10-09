"""Test battery config flow."""

# Test data for battery flow
VALID_DATA = [
    {
        "description": "Basic battery configuration",
        "config": {
            "name_value": "Test Battery",
            "capacity_value": 10000,
            "initial_charge_percentage_value": "sensor.battery_soc",
            "max_charge_power_value": 5000,
            "max_discharge_power_value": 5000,
            "charge_cost_value": 0.0,
            "discharge_cost_value": 0.0,
        },
    },
    {
        "description": "Advanced battery configuration with efficiency and limits",
        "config": {
            "name_value": "Advanced Battery",
            "capacity_value": 10000,
            "initial_charge_percentage_value": "sensor.battery_soc",
            "min_charge_percentage_value": 10,
            "max_charge_percentage_value": 90,
            "max_charge_power_value": 5000,
            "max_discharge_power_value": 5000,
            "efficiency_value": 0.95,
            "charge_cost_value": 0.05,
            "discharge_cost_value": 0.03,
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {
            "name_value": "",
            "capacity_value": 5000,
            "initial_charge_percentage_value": "sensor.battery_soc",
            "max_charge_power_value": 5000,
            "max_discharge_power_value": 5000,
            "charge_cost_value": 0.0,
            "discharge_cost_value": 0.0,
        },
        "error": "cannot be empty",
    },
    {
        "description": "Negative capacity should fail validation",
        "config": {
            "name_value": "Test Battery",
            "capacity_value": -1000,
            "initial_charge_percentage_value": "sensor.battery_soc",
            "max_charge_power_value": 5000,
            "max_discharge_power_value": 5000,
            "charge_cost_value": 0.0,
            "discharge_cost_value": 0.0,
        },
        "error": "value must be positive",
    },
]
