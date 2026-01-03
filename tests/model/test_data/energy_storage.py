"""Test data and factories for EnergyStorage element."""

from custom_components.haeo.model.energy_storage import EnergyStorage

from .element_types import ElementTestCase

VALID_CASES: list[ElementTestCase] = [
    {
        "description": "EnergyStorage charging with fixed input",
        "factory": EnergyStorage,
        "data": {
            "name": "storage_charging",
            "periods": [1.0] * 3,
            "capacity": 10.0,
            "initial_charge": 2.0,
        },
        "inputs": {
            "power": [5.0, 2.0, 0.0],  # Forced input
            "input_cost": 0.0,
            "output_cost": 0.0,
        },
        "expected_outputs": {
            "energy_storage_energy_stored": {"type": "energy", "unit": "kWh", "values": (2.0, 7.0, 9.0, 9.0)},
            "energy_storage_power_charge": {"type": "power", "unit": "kW", "values": (5.0, 2.0, 0.0)},
            "energy_storage_power_discharge": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "energy_storage_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0, 0.0)},
            "energy_storage_energy_in_flow": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "energy_storage_energy_out_flow": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "energy_storage_soc_max": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "energy_storage_soc_min": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
        },
    },
    {
        "description": "EnergyStorage discharging with fixed output",
        "factory": EnergyStorage,
        "data": {
            "name": "storage_discharging",
            "periods": [1.0] * 3,
            "capacity": 10.0,
            "initial_charge": 8.0,
        },
        "inputs": {
            "power": [-3.0, -3.0, 0.0],  # Forced output
            "input_cost": 0.0,
            "output_cost": 0.0,
        },
        "expected_outputs": {
            "energy_storage_energy_stored": {"type": "energy", "unit": "kWh", "values": (8.0, 5.0, 2.0, 2.0)},
            "energy_storage_power_charge": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "energy_storage_power_discharge": {"type": "power", "unit": "kW", "values": (3.0, 3.0, 0.0)},
            "energy_storage_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0, 0.0)},
            "energy_storage_energy_in_flow": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "energy_storage_energy_out_flow": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "energy_storage_soc_max": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "energy_storage_soc_min": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
        },
    },
    {
        "description": "EnergyStorage with fixed load pattern",
        "factory": EnergyStorage,
        "data": {
            "name": "storage_fixed",
            "periods": [1.0] * 3,
            "capacity": 10.0,
            "initial_charge": 5.0,
        },
        "inputs": {
            "power": [2.0, -1.0, 1.0],  # Positive=charge, negative=discharge
            "input_cost": 0.0,
            "output_cost": 0.0,
        },
        "expected_outputs": {
            "energy_storage_energy_stored": {"type": "energy", "unit": "kWh", "values": (5.0, 7.0, 6.0, 7.0)},
            "energy_storage_power_charge": {"type": "power", "unit": "kW", "values": (2.0, 0.0, 1.0)},
            "energy_storage_power_discharge": {"type": "power", "unit": "kW", "values": (0.0, 1.0, 0.0)},
            "energy_storage_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0, 0.0)},
            "energy_storage_energy_in_flow": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "energy_storage_energy_out_flow": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "energy_storage_soc_max": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
            "energy_storage_soc_min": {"type": "shadow_price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
        },
    },
]

INVALID_CASES: list[ElementTestCase] = []
INVALID_MODEL_PARAMS: list[ElementTestCase] = []
