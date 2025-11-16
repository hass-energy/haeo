"""Test data and factories for Battery element."""

from typing import Any

from custom_components.haeo.model.battery import Battery

VALID_CASES = [
    {
        "description": "Battery charging from infinite source",
        "factory": Battery,
        "data": {
            "name": "battery_charging",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 20.0,
            "min_charge_percentage": 10.0,
            "max_charge_percentage": 90.0,
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
            "efficiency": 95.0,
        },
        "inputs": {
            "power": [None, None, None],  # Infinite (unbounded)
            "cost": -0.1,  # Negative cost = benefit for consuming (encourages charging)
        },
        "expected_outputs": {
            "power_consumed": {"type": "power", "unit": "kW", "values": (5.0, 5.0, 5.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (2.375, 0.0, 0.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (2.0, 4.25, 9.0)},
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (20.0, 42.5, 90.0)},
            "price_consumption": {"type": "price", "unit": "$/kWh", "values": (0.0, -0.0005, -0.001)},
        },
    },
    {
        "description": "Battery discharging to infinite sink",
        "factory": Battery,
        "data": {
            "name": "battery_discharging",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 80.0,
            "min_charge_percentage": 10.0,
            "max_charge_percentage": 90.0,
            "max_charge_power": 5.0,
            "max_discharge_power": 3.0,
            "efficiency": 95.0,
        },
        "inputs": {
            "power": [None, None, None],  # Infinite (unbounded)
            "cost": 0.1,  # Positive cost = benefit for providing power (encourages discharging)
        },
        "expected_outputs": {
            "power_consumed": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (3.0, 3.0, 3.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (8.0, 4.842105263157895, 1.6842105263157894)},
            "battery_state_of_charge": {
                "type": "soc",
                "unit": "%",
                "values": (80.0, 48.421052631578945, 16.842105263157894),
            },
            "price_consumption": {"type": "price", "unit": "$/kWh", "values": (0.0, -0.0005, -0.001)},
        },
    },
    {
        "description": "Battery with fixed load pattern",
        "factory": Battery,
        "data": {
            "name": "battery_fixed",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 50.0,
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
            "efficiency": 100.0,
        },
        "inputs": {
            "power": [2.0, -1.0, 1.0],  # Positive=charge, negative=discharge
            "cost": 0.0,
        },
        "expected_outputs": {
            "power_consumed": {"type": "power", "unit": "kW", "values": (2.0, 0.0, 1.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (0.0, 1.0, 0.0)},
            "energy_stored": {"type": "energy", "unit": "kWh", "values": (5.0, 7.0, 6.0)},
            "battery_state_of_charge": {"type": "soc", "unit": "%", "values": (50.0, 70.0, 60.0)},
            "price_consumption": {"type": "price", "unit": "$/kWh", "values": (0.0, -0.0005, -0.001)},
        },
    },
]

INVALID_CASES: list[dict[str, Any]] = [
    {
        "description": "Battery capacity array length mismatch",
        "element_class": Battery,
        "data": {
            "name": "test_battery",
            "period": 1.0,
            "n_periods": 3,
            "capacity": [10.0, 10.0],  # Only 2 values for 3 periods
            "initial_charge_percentage": 50.0,
            "min_charge_percentage": 20.0,
            "max_charge_percentage": 80.0,
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
            "efficiency": 95.0,
        },
        "expected_error": "Sequence length .* must match n_periods",
    },
    {
        "description": "Battery min_charge_percentage greater than max_charge_percentage",
        "element_class": Battery,
        "data": {
            "name": "test_battery",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 50.0,
            "min_charge_percentage": 80.0,  # Greater than max
            "max_charge_percentage": 20.0,
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
            "efficiency": 95.0,
        },
        "expected_error": "min_charge_percentage .* must be less than max_charge_percentage",
    },
    {
        "description": "Battery undercharge_percentage greater than min_charge_percentage",
        "element_class": Battery,
        "data": {
            "name": "test_battery",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 50.0,
            "min_charge_percentage": 20.0,
            "max_charge_percentage": 80.0,
            "undercharge_percentage": 30.0,  # Greater than min
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
            "efficiency": 95.0,
        },
        "expected_error": "undercharge_percentage .* must be less than min_charge_percentage",
    },
    {
        "description": "Battery max_charge_percentage greater than overcharge_percentage",
        "element_class": Battery,
        "data": {
            "name": "test_battery",
            "period": 1.0,
            "n_periods": 3,
            "capacity": 10.0,
            "initial_charge_percentage": 50.0,
            "min_charge_percentage": 20.0,
            "max_charge_percentage": 80.0,
            "overcharge_percentage": 70.0,  # Less than max
            "max_charge_power": 5.0,
            "max_discharge_power": 5.0,
            "efficiency": 95.0,
        },
        "expected_error": "overcharge_percentage .* must be greater than max_charge_percentage",
    },
]
