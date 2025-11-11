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
]

INVALID_CASES: list[dict[str, Any]] = []
