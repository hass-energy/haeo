"""Test data and factories for Photovoltaics element."""

from haeo_core.model.photovoltaics import Photovoltaics

from .element_types import ElementTestCase

VALID_CASES: list[ElementTestCase] = [
    {
        "description": "Photovoltaics full production without curtailment",
        "factory": Photovoltaics,
        "data": {
            "name": "pv_no_curtailment",
            "period": 1.0,
            "n_periods": 3,
            "forecast": [5.0, 10.0, 8.0],
            "curtailment": False,
        },
        "inputs": {
            "power": [None, None, None],  # Infinite sink (unbounded)
        },
        "expected_outputs": {
            "power_available": {"type": "power", "unit": "kW", "values": (5.0, 10.0, 8.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (5.0, 10.0, 8.0)},
        },
    },
    {
        "description": "Photovoltaics with curtailment due to negative benefit",
        "factory": Photovoltaics,
        "data": {
            "name": "pv_curtailment",
            "period": 1.0,
            "n_periods": 3,
            "forecast": [5.0, 10.0, 8.0],
            "curtailment": True,
            "price_production": [0.0, 0.0, 0.0],
        },
        "inputs": {
            "power": [None, None, None],  # Infinite
            "input_cost": -0.1,  # Negative cost with negative power_vars gives positive total (discourages production)
            "output_cost": 0.1,
        },
        "expected_outputs": {
            "power_available": {"type": "power", "unit": "kW", "values": (5.0, 10.0, 8.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "price_production": {"type": "price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
        },
    },
    {
        "description": "Photovoltaics with production cost outweighing benefit",
        "factory": Photovoltaics,
        "data": {
            "name": "pv_cost",
            "period": 1.0,
            "n_periods": 3,
            "forecast": [5.0, 10.0, 8.0],
            "curtailment": True,
            "price_production": [0.5, 0.5, 0.5],  # High production cost
        },
        "inputs": {
            "power": [None, None, None],
            "input_cost": 0.1,  # Low benefit for consuming
            "output_cost": -0.1,
        },
        "expected_outputs": {
            "power_available": {"type": "power", "unit": "kW", "values": (5.0, 10.0, 8.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "price_production": {"type": "price", "unit": "$/kWh", "values": (0.5, 0.5, 0.5)},
        },
    },
    {
        "description": "Photovoltaics zero cost production with benefit",
        "factory": Photovoltaics,
        "data": {
            "name": "pv_beneficial",
            "period": 1.0,
            "n_periods": 3,
            "forecast": [5.0, 10.0, 8.0],
            "curtailment": True,
            "price_production": [0.0, 0.0, 0.0],
        },
        "inputs": {
            "power": [None, None, None],
            "input_cost": 0.2,  # Positive cost with negative power_vars gives negative total (encourages production)
            "output_cost": -0.2,
        },
        "expected_outputs": {
            "power_available": {"type": "power", "unit": "kW", "values": (5.0, 10.0, 8.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (5.0, 10.0, 8.0)},
            "price_production": {"type": "price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
        },
    },
]

INVALID_CASES: list[ElementTestCase] = [
    {
        "description": "Photovoltaics with forecast length mismatch",
        "factory": Photovoltaics,
        "data": {
            "name": "pv_forecast_mismatch",
            "period": 1.0,
            "n_periods": 3,
            "forecast": (1.2, 1.4),  # Only 2 instead of 3
            "price_production": (0.1, 0.2, 0.3),
            "curtailment": False,
        },
        "expected_error": "Sequence length .* must match n_periods",
    },
    {
        "description": "Photovoltaics with price_production length mismatch",
        "factory": Photovoltaics,
        "data": {
            "name": "pv_price_mismatch",
            "period": 1.0,
            "n_periods": 3,
            "forecast": (1.2, 1.4, 1.6),
            "price_production": (0.1, 0.2),  # Only 2 instead of 3
            "curtailment": False,
        },
        "expected_error": "Sequence length .* must match n_periods",
    },
]
