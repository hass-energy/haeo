"""Test data and factories for Load element."""

from custom_components.haeo.model.load import Load

from .element_types import ElementTestCase

VALID_CASES: list[ElementTestCase] = [
    {
        "description": "Load with varying consumption",
        "factory": Load,
        "data": {
            "name": "load",
            "period": 1.0,
            "n_periods": 3,
        },
        "inputs": {
            "power": [1.0, 1.5, 2.0],  # Power flowing into load (consumption)
            "input_cost": 0.1,
        },
        "expected_outputs": {
            "load_power_consumed": {"type": "power", "unit": "kW", "values": (1.0, 1.5, 2.0)},
            "load_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0, 0.0)},
        },
    },
    {
        "description": "Load with zero consumption",
        "factory": Load,
        "data": {
            "name": "load_zero",
            "period": 1.0,
            "n_periods": 2,
        },
        "inputs": {
            "power": [0.0, 0.0],
            "input_cost": 0.0,
        },
        "expected_outputs": {
            "load_power_consumed": {"type": "power", "unit": "kW", "values": (0.0, 0.0)},
            "load_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
        },
    },
    {
        "description": "Load with high consumption",
        "factory": Load,
        "data": {
            "name": "load_high",
            "period": 1.0,
            "n_periods": 4,
        },
        "inputs": {
            "power": [10.0, 15.0, 12.0, 8.0],
            "input_cost": 0.0,
        },
        "expected_outputs": {
            "load_power_consumed": {"type": "power", "unit": "kW", "values": (10.0, 15.0, 12.0, 8.0)},
            "load_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0, 0.0, 0.0)},
        },
    },
]

INVALID_CASES: list[ElementTestCase] = []
