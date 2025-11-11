"""Test data for battery element configuration."""

from typing import Any

# Valid battery configurations
VALID: list[dict[str, Any]] = [
    {
        "data": {
            "element_type": "battery",
            "name": "Test Battery",
            "capacity": 10.0,
            "initial_charge_percentage": 50.0,
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
        },
        "description": "Standard battery with all fields",
    },
    {
        "data": {
            "element_type": "battery",
            "name": "Sensor SOC Battery",
            "capacity": 13.5,
            "initial_charge_percentage": "sensor.battery_soc",
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
        },
        "description": "Battery with sensor for initial SOC",
    },
    {
        "data": {
            "element_type": "battery",
            "name": "Min Charge Battery",
            "capacity": 10.0,
            "initial_charge_percentage": 50.0,
            "min_charge_percentage": 10.0,
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
        },
        "description": "Battery with minimum charge constraint",
    },
    {
        "data": {
            "element_type": "battery",
            "name": "Max Charge Battery",
            "capacity": 10.0,
            "initial_charge_percentage": 50.0,
            "max_charge_percentage": 90.0,
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
        },
        "description": "Battery with maximum charge constraint",
    },
    {
        "data": {
            "element_type": "battery",
            "name": "High Efficiency Battery",
            "capacity": 10.0,
            "initial_charge_percentage": 50.0,
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
            "efficiency": 0.98,
        },
        "description": "Battery with custom efficiency",
    },
]
# Invalid battery configurations
INVALID: list[dict[str, Any]] = [
    {
        "data": {
            "element_type": "battery",
            "name": "Negative Capacity",
            "capacity": -10.0,
            "initial_charge_percentage": 50.0,
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
        },
        "description": "Battery with negative capacity (should fail validation)",
    },
    {
        "data": {
            "element_type": "battery",
            "name": "Invalid SOC",
            "capacity": 10.0,
            "initial_charge_percentage": 150.0,
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
        },
        "description": "Battery with SOC > 100%",
    },
    {
        "data": {
            "element_type": "battery",
            "name": "Missing Capacity",
            "initial_charge_percentage": 50.0,
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
        },
        "description": "Battery missing required capacity field",
    },
    {
        "data": {
            "element_type": "battery",
            "name": "None Initial Charge",
            "capacity": 10.0,
            "initial_charge_percentage": None,
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
        },
        "description": "Battery with None initial_charge_percentage",
    },
    {
        "data": {
            "element_type": "battery",
            "name": "Zero Capacity",
            "capacity": 0.0,
            "initial_charge_percentage": 0.0,
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
        },
        "description": "Battery with zero capacity",
    },
]
