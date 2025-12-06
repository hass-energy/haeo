"""Test data and factories for Photovoltaics element."""

from custom_components.haeo.model.photovoltaics import Photovoltaics

from .element_types import ElementTestCase

VALID_CASES: list[ElementTestCase] = [
    {
        "description": "Photovoltaics full production",
        "factory": Photovoltaics,
        "data": {
            "name": "pv_production",
            "period": 1.0,
            "n_periods": 3,
        },
        "inputs": {
            "power": [-5.0, -10.0, -8.0],  # Negative power = producing (flowing out)
            "output_cost": -0.1,  # Benefit for producing
        },
        "expected_outputs": {
            "photovoltaics_power_produced": {"type": "power", "unit": "kW", "values": (5.0, 10.0, 8.0)},
            "photovoltaics_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0, 0.0)},
        },
    },
    {
        "description": "Photovoltaics with zero production",
        "factory": Photovoltaics,
        "data": {
            "name": "pv_zero",
            "period": 1.0,
            "n_periods": 3,
        },
        "inputs": {
            "power": [0.0, 0.0, 0.0],
            "output_cost": 0.0,
        },
        "expected_outputs": {
            "photovoltaics_power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "photovoltaics_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0, 0.0)},
        },
    },
    {
        "description": "Photovoltaics with varying production",
        "factory": Photovoltaics,
        "data": {
            "name": "pv_varying",
            "period": 1.0,
            "n_periods": 4,
        },
        "inputs": {
            "power": [-2.0, -5.0, -3.0, -1.0],  # Negative = producing
            "output_cost": -0.05,
        },
        "expected_outputs": {
            "photovoltaics_power_produced": {"type": "power", "unit": "kW", "values": (2.0, 5.0, 3.0, 1.0)},
            "photovoltaics_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0, 0.0, 0.0)},
        },
    },
]

INVALID_CASES: list[ElementTestCase] = []
