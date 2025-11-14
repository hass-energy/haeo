"""Test data and factories for Grid element."""

from custom_components.haeo.model.grid import Grid

VALID_CASES = [
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
            "power": [5.0, 8.0, 6.0],  # Fixed load (positive = import needed)
            "cost": 0.0,
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
            "power": [-3.0, -5.0, -4.0],  # Fixed generation (negative = export)
            "cost": 0.0,
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
            "power": [5.0, 5.0],  # Exactly at limit
            "cost": 0.0,
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
            "power": [-4.0, -4.0],  # Exactly at limit (negative = export)
            "cost": 0.0,
        },
        "expected_outputs": {
            "power_imported": {"type": "power", "unit": "kW", "values": (0.0, 0.0)},
            "power_exported": {"type": "power", "unit": "kW", "values": (4.0, 4.0)},
            "price_export": {"type": "price", "unit": "$/kWh", "values": (0.05, 0.08)},
        },
    },
]

INVALID_CASES = [
    {
        "description": "Grid with import_price length mismatch",
        "element_class": Grid,
        "data": {
            "name": "grid",
            "period": 1.0,
            "n_periods": 2,
            "import_limit": 5.0,
            "export_limit": 4.0,
            "import_price": (0.3,),  # Only 1 instead of 2
            "export_price": (0.1, 0.2),
        },
        "expected_error": "import_price must contain 2 entries",
    },
    {
        "description": "Grid with export_price length mismatch",
        "element_class": Grid,
        "data": {
            "name": "grid",
            "period": 1.0,
            "n_periods": 2,
            "import_limit": 5.0,
            "export_limit": 4.0,
            "import_price": (0.3, 0.4),
            "export_price": (0.1,),  # Only 1 instead of 2
        },
        "expected_error": "export_price must contain 2 entries",
    },
]
