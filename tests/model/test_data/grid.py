"""Test data and factories for Grid element."""

from custom_components.haeo.model.grid import Grid

from .element_types import ElementTestCase

VALID_CASES: list[ElementTestCase] = [
    {
        "description": "Grid importing power for fixed load",
        "factory": Grid,
        "data": {
            "name": "grid_import",
            "period": 1.0,
            "n_periods": 3,
        },
        "inputs": {
            "power": [-5.0, -8.0, -6.0],  # Negative = import (from grid perspective, production)
        },
        "expected_outputs": {
            "grid_power_imported": {"type": "power", "unit": "kW", "values": (5.0, 8.0, 6.0)},
            "grid_power_exported": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "grid_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0, 0.0)},
        },
    },
    {
        "description": "Grid exporting power from fixed source",
        "factory": Grid,
        "data": {
            "name": "grid_export",
            "period": 1.0,
            "n_periods": 3,
        },
        "inputs": {
            "power": [3.0, 5.0, 4.0],  # Positive = export (from grid perspective, consumption)
        },
        "expected_outputs": {
            "grid_power_imported": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "grid_power_exported": {"type": "power", "unit": "kW", "values": (3.0, 5.0, 4.0)},
            "grid_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0, 0.0)},
        },
    },
    {
        "description": "Grid respecting import limit",
        "factory": Grid,
        "data": {
            "name": "grid_import_limit",
            "period": 1.0,
            "n_periods": 2,
        },
        "inputs": {
            "power": [-5.0, -5.0],  # Negative = import (at limit)
        },
        "expected_outputs": {
            "grid_power_imported": {"type": "power", "unit": "kW", "values": (5.0, 5.0)},
            "grid_power_exported": {"type": "power", "unit": "kW", "values": (0.0, 0.0)},
            "grid_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
        },
    },
    {
        "description": "Grid respecting export limit",
        "factory": Grid,
        "data": {
            "name": "grid_export_limit",
            "period": 1.0,
            "n_periods": 2,
        },
        "inputs": {
            "power": [4.0, 4.0],  # Positive = export (at limit)
        },
        "expected_outputs": {
            "grid_power_imported": {"type": "power", "unit": "kW", "values": (0.0, 0.0)},
            "grid_power_exported": {"type": "power", "unit": "kW", "values": (4.0, 4.0)},
            "grid_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0)},
        },
    },
]

INVALID_CASES: list[ElementTestCase] = []
