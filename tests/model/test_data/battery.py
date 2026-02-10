"""Test data and factories for Battery element."""

import numpy as np

from custom_components.haeo.model.elements.battery import Battery

from .element_types import ElementTestCase

VALID_CASES: list[ElementTestCase] = [
    {
        "description": "Battery charging with fixed input",
        "factory": Battery,
        "data": {
            "name": "battery_charging",
            "periods": np.array([1.0] * 3),
            "capacity": 10.0,
            "initial_charge": 2.0,
        },
        "inputs": {
            "power": [5.0, 2.0, 0.0],  # Forced input
            "input_cost": 0.0,
            "output_cost": 0.0,
        },
        "expected_outputs": {
            "battery_energy_stored": {"type": "energy", "unit": "kWh", "values": (2.0, 7.0, 9.0, 9.0)},
            "battery_power_charge": {"type": "power", "unit": "kW", "values": (5.0, 2.0, 0.0)},
            "battery_power_discharge": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "battery_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0, 0.0)},
            "battery_energy_in_flow": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "battery_energy_out_flow": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "battery_soc_max": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "battery_soc_min": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
        },
    },
    {
        "description": "Battery charging with salvage value",
        "factory": Battery,
        "data": {
            "name": "battery_charging_salvage",
            "periods": np.array([1.0] * 3),
            "capacity": 10.0,
            "initial_charge": 2.0,
            "salvage_value": 0.2,
        },
        "inputs": {
            "power": [5.0, 2.0, 0.0],
            "input_cost": 0.0,
            "output_cost": 0.0,
        },
        "expected_outputs": {
            "battery_energy_stored": {"type": "energy", "unit": "kWh", "values": (2.0, 7.0, 9.0, 9.0)},
            "battery_power_charge": {"type": "power", "unit": "kW", "values": (5.0, 2.0, 0.0)},
            "battery_power_discharge": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "battery_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.2, 0.2, 0.2)},
            "battery_energy_in_flow": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "battery_energy_out_flow": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "battery_soc_max": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "battery_soc_min": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
        },
    },
    {
        "description": "Battery discharging with fixed output",
        "factory": Battery,
        "data": {
            "name": "battery_discharging",
            "periods": np.array([1.0] * 3),
            "capacity": 10.0,
            "initial_charge": 8.0,
        },
        "inputs": {
            "power": [-3.0, -3.0, 0.0],  # Forced output
            "input_cost": 0.0,
            "output_cost": 0.0,
        },
        "expected_outputs": {
            "battery_energy_stored": {"type": "energy", "unit": "kWh", "values": (8.0, 5.0, 2.0, 2.0)},
            "battery_power_charge": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "battery_power_discharge": {"type": "power", "unit": "kW", "values": (3.0, 3.0, 0.0)},
            "battery_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0, 0.0)},
            "battery_energy_in_flow": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "battery_energy_out_flow": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "battery_soc_max": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "battery_soc_min": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
        },
    },
    {
        "description": "Battery with fixed load pattern",
        "factory": Battery,
        "data": {
            "name": "battery_fixed",
            "periods": np.array([1.0] * 3),
            "capacity": 10.0,
            "initial_charge": 5.0,
        },
        "inputs": {
            "power": [2.0, -1.0, 1.0],  # Positive=charge, negative=discharge
            "input_cost": 0.0,
            "output_cost": 0.0,
        },
        "expected_outputs": {
            "battery_energy_stored": {"type": "energy", "unit": "kWh", "values": (5.0, 7.0, 6.0, 7.0)},
            "battery_power_charge": {"type": "power", "unit": "kW", "values": (2.0, 0.0, 1.0)},
            "battery_power_discharge": {"type": "power", "unit": "kW", "values": (0.0, 1.0, 0.0)},
            "battery_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0, 0.0)},
            "battery_energy_in_flow": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "battery_energy_out_flow": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "battery_soc_max": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "battery_soc_min": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
        },
    },
]

INVALID_CASES: list[ElementTestCase] = []
INVALID_MODEL_PARAMS: list[ElementTestCase] = []
