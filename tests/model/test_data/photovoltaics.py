"""Test data and factories for Photovoltaics element."""

from typing import Any

from custom_components.haeo.model.photovoltaics import Photovoltaics

VALID_CASES = [
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
            "cost": 0.0,
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
            "cost": -0.1,  # Negative cost with negative power_vars gives positive total (discourages production)
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
            "cost": 0.1,  # Low benefit for consuming
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
            "cost": 0.2,  # Positive cost with negative power_vars gives negative total (encourages production)
        },
        "expected_outputs": {
            "power_available": {"type": "power", "unit": "kW", "values": (5.0, 10.0, 8.0)},
            "power_produced": {"type": "power", "unit": "kW", "values": (5.0, 10.0, 8.0)},
            "price_production": {"type": "price", "unit": "$/kWh", "values": (0.0, 0.0, 0.0)},
        },
    },
]

INVALID_CASES = [
    {
        "description": "Photovoltaics with forecast length mismatch",
        "element_class": Photovoltaics,
        "data": {
            "name": "photovoltaics",
            "period": 1.0,
            "n_periods": 2,
            "forecast": (1.2,),  # Only 1 instead of 2
            "price_production": (0.1, 0.2),
            "price_consumption": (0.3, 0.4),
        },
        "expected_error": "forecast length",
    },
    {
        "description": "Photovoltaics with price_production length mismatch",
        "element_class": Photovoltaics,
        "data": {
            "name": "photovoltaics",
            "period": 1.0,
            "n_periods": 2,
            "forecast": (1.2, 1.4),
            "price_production": (0.1,),  # Only 1 instead of 2
            "price_consumption": (0.3, 0.4),
        },
        "expected_error": "price_production length",
    },
    {
        "description": "Photovoltaics with price_consumption length mismatch",
        "element_class": Photovoltaics,
        "data": {
            "name": "photovoltaics",
            "period": 1.0,
            "n_periods": 2,
            "forecast": (1.2, 1.4),
            "price_production": (0.1, 0.2),
            "price_consumption": (0.3,),  # Only 1 instead of 2
        },
        "expected_error": "price_consumption length",
    },
]
