"""Test data and factories for Battery element."""

from custom_components.haeo.model.battery import Battery

from .element_types import ElementTestCase

VALID_CASES: list[ElementTestCase] = [
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
            "input_cost": -0.1,  # Negative cost = benefit for consuming (encourages charging)
            "output_cost": 0.1,
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
            "input_cost": 0.1,  # Positive cost = benefit for providing power (encourages discharging)
            "output_cost": -0.1,
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
            "input_cost": 0.0,
            "output_cost": 0.0,
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

INVALID_CASES: list[ElementTestCase] = [
    {
        "description": "Battery with capacity length mismatch",
        "factory": Battery,
        "data": {
            "name": "invalid_battery",
            "period": 1.0,
            "n_periods": 3,
            "capacity": [10.0, 10.0],  # Length 2, should be 3
            "initial_charge_percentage": 50.0,
        },
        "expected_error": "Sequence length .* must match n_periods",
    },
]
