"""Test data and factories for Connection element."""

from typing import Any

from custom_components.haeo.model.connection import Connection

from . import fix_lp_variable


def create(data: dict[str, Any]) -> Connection:
    """Create a test Connection instance with fixed values."""

    connection = Connection(**data)

    for index, variable in enumerate(connection.power):
        fix_lp_variable(variable, float(index + 1))

    return connection


VALID_CASES = [
    {
        "description": "Connection between two nodes",
        "factory": create,
        "data": {
            "name": "grid_link",
            "period": 1.0,
            "n_periods": 3,
            "source": "battery",
            "target": "grid",
        },
        "expected_outputs": {
            "power_flow": {"type": "power", "unit": "kW", "values": (1.0, 2.0, 3.0)},
        },
    },
    {
        "description": "Connection with power limits",
        "factory": create,
        "data": {
            "name": "limited_connection",
            "period": 1.0,
            "n_periods": 2,
            "source": "solar",
            "target": "battery",
            "min_power": -5.0,
            "max_power": 10.0,
        },
        "expected_outputs": {
            "power_flow": {"type": "power", "unit": "kW", "values": (1.0, 2.0)},
        },
    },
]

INVALID_CASES: list[dict[str, Any]] = []
