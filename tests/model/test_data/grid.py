"""Test data and factories for Grid element."""

from typing import Any

from pulp import LpVariable

from custom_components.haeo.model.grid import Grid

from . import fix_lp_variable


def create(data: dict[str, Any]) -> Grid:
    """Create a test Grid instance with fixed values."""

    grid = Grid(**data)

    if grid.power_consumption is not None:
        for index, variable in enumerate(grid.power_consumption):
            if isinstance(variable, LpVariable):
                fix_lp_variable(variable, float(index + 1))
    if grid.power_production is not None:
        for index, variable in enumerate(grid.power_production):
            if isinstance(variable, LpVariable):
                fix_lp_variable(variable, float(index + 1))

    return grid


VALID_CASES = [
    {
        "description": "Grid with valid import/export prices",
        "factory": create,
        "data": {
            "name": "grid",
            "period": 1.0,
            "n_periods": 2,
            "import_limit": 5.0,
            "export_limit": 4.0,
            "import_price": (0.3, 0.4),
            "export_price": (0.1, 0.2),
        },
        "expected_outputs": {
            "power_exported": {"type": "power", "unit": "kW", "values": (1.0, 2.0)},
            "power_imported": {"type": "power", "unit": "kW", "values": (1.0, 2.0)},
            "price_export": {"type": "price", "unit": "$/kWh", "values": (0.1, 0.2)},
            "price_import": {"type": "price", "unit": "$/kWh", "values": (0.3, 0.4)},
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
