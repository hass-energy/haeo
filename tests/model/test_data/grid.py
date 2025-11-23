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
            "import_limit": 10.0,
            "export_limit": 5.0,
            "import_price": [0.1, 0.2, 0.15],
            "export_price": [0.05, 0.08, 0.06],
        },
        "inputs": {
            "power": [-5.0, -8.0, -6.0],  # Negative = import (from grid perspective, production)
        },
        "expected_outputs": {
            "power_imported": {"type": "power", "unit": "kW", "values": (5.0, 8.0, 6.0)},
            "power_exported": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "price_import": {"type": "price", "unit": "$/kWh", "values": (0.1, 0.2, 0.15)},
            "price_export": {"type": "price", "unit": "$/kWh", "values": (0.05, 0.08, 0.06)},
        },
    },
    {
        "description": "Grid exporting power from fixed source",
        "factory": Grid,
        "data": {
            "name": "grid_export",
            "period": 1.0,
            "n_periods": 3,
            "import_limit": 10.0,
            "export_limit": 5.0,
            "import_price": [0.1, 0.2, 0.15],
            "export_price": [0.05, 0.08, 0.06],
        },
        "inputs": {
            "power": [3.0, 5.0, 4.0],  # Positive = export (from grid perspective, consumption)
        },
        "expected_outputs": {
            "power_imported": {"type": "power", "unit": "kW", "values": (0.0, 0.0, 0.0)},
            "power_exported": {"type": "power", "unit": "kW", "values": (3.0, 5.0, 4.0)},
            "price_import": {"type": "price", "unit": "$/kWh", "values": (0.1, 0.2, 0.15)},
            "price_export": {"type": "price", "unit": "$/kWh", "values": (0.05, 0.08, 0.06)},
        },
    },
    {
        "description": "Grid respecting import limit",
        "factory": Grid,
        "data": {
            "name": "grid_import_limit",
            "period": 1.0,
            "n_periods": 2,
            "import_limit": 5.0,
            "import_price": [0.1, 0.2],
        },
        "inputs": {
            "power": [-5.0, -5.0],  # Negative = import (at limit)
        },
        "expected_outputs": {
            "power_imported": {"type": "power", "unit": "kW", "values": (5.0, 5.0)},
            "power_exported": {"type": "power", "unit": "kW", "values": (0.0, 0.0)},
            "price_import": {"type": "price", "unit": "$/kWh", "values": (0.1, 0.2)},
        },
    },
    {
        "description": "Grid respecting export limit",
        "factory": Grid,
        "data": {
            "name": "grid_export_limit",
            "period": 1.0,
            "n_periods": 2,
            "export_limit": 4.0,
            "export_price": [0.05, 0.08],
        },
        "inputs": {
            "power": [4.0, 4.0],  # Positive = export (at limit)
        },
        "expected_outputs": {
            "power_imported": {"type": "power", "unit": "kW", "values": (0.0, 0.0)},
            "power_exported": {"type": "power", "unit": "kW", "values": (4.0, 4.0)},
            "price_export": {"type": "price", "unit": "$/kWh", "values": (0.05, 0.08)},
        },
    },
]

INVALID_CASES: list[ElementTestCase] = [
    {
        "description": "Grid with import_price length mismatch",
        "factory": Grid,
        "data": {
            "name": "grid_import_mismatch",
            "period": 1.0,
            "n_periods": 3,
            "import_limit": 5.0,
            "export_limit": 4.0,
            "import_price": (0.3, 0.4),  # Only 2 instead of 3
            "export_price": (0.1, 0.2, 0.3),
        },
        "expected_error": "Sequence length .* must match n_periods",
    },
    {
        "description": "Grid with export_price length mismatch",
        "factory": Grid,
        "data": {
            "name": "grid_export_mismatch",
            "period": 1.0,
            "n_periods": 3,
            "import_limit": 5.0,
            "export_limit": 4.0,
            "import_price": (0.3, 0.4, 0.5),
            "export_price": (0.1, 0.2),  # Only 2 instead of 3
        },
        "expected_error": "Sequence length .* must match n_periods",
    },
]
