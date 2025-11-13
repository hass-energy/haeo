"""Test data and factories for Connection element."""

from typing import Any

from custom_components.haeo.model.connection import Connection

from . import fix_lp_variable


def create(data: dict[str, Any]) -> Connection:
    """Create a test Connection instance with fixed values."""

    connection = Connection(**data)

    for index, variable in enumerate(connection.power_source_target):
        fix_lp_variable(variable, float(index + 1))

    for index, variable in enumerate(connection.power_target_source):
        fix_lp_variable(variable, float(index + 0.5))

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
            "power_flow_source_target": {"type": "power", "unit": "kW", "values": (1.0, 2.0, 3.0)},
            "power_flow_target_source": {"type": "power", "unit": "kW", "values": (0.5, 1.5, 2.5)},
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
            "max_power_source_target": 5.0,
            "max_power_target_source": 10.0,
        },
        "expected_outputs": {
            "power_flow_source_target": {"type": "power", "unit": "kW", "values": (1.0, 2.0)},
            "power_flow_target_source": {"type": "power", "unit": "kW", "values": (0.5, 1.5)},
        },
    },
    {
        "description": "Connection with efficiency",
        "factory": create,
        "data": {
            "name": "inverter_connection",
            "period": 1.0,
            "n_periods": 2,
            "source": "dc_net",
            "target": "ac_net",
            "max_power_source_target": 5.0,
            "max_power_target_source": 5.0,
            "efficiency_source_target": 95.0,
            "efficiency_target_source": 94.0,
        },
        "expected_outputs": {
            "power_flow_source_target": {"type": "power", "unit": "kW", "values": (1.0, 2.0)},
            "power_flow_target_source": {"type": "power", "unit": "kW", "values": (0.5, 1.5)},
        },
    },
    {
        "description": "Connection with pricing",
        "factory": create,
        "data": {
            "name": "priced_connection",
            "period": 1.0,
            "n_periods": 3,
            "source": "node_a",
            "target": "node_b",
            "price_source_target": [0.1, 0.2, 0.15],
            "price_target_source": [0.12, 0.18, 0.14],
        },
        "expected_outputs": {
            "power_flow_source_target": {"type": "power", "unit": "kW", "values": (1.0, 2.0, 3.0)},
            "power_flow_target_source": {"type": "power", "unit": "kW", "values": (0.5, 1.5, 2.5)},
        },
    },
    {
        "description": "Connection with time-varying power limits",
        "factory": create,
        "data": {
            "name": "varying_connection",
            "period": 1.0,
            "n_periods": 3,
            "source": "grid",
            "target": "net",
            "max_power_source_target": [10.0, 8.0, 12.0],
            "max_power_target_source": [5.0, 6.0, 4.0],
        },
        "expected_outputs": {
            "power_flow_source_target": {"type": "power", "unit": "kW", "values": (1.0, 2.0, 3.0)},
            "power_flow_target_source": {"type": "power", "unit": "kW", "values": (0.5, 1.5, 2.5)},
        },
    },
    {
        "description": "Connection with time-varying efficiency",
        "factory": create,
        "data": {
            "name": "varying_efficiency_connection",
            "period": 1.0,
            "n_periods": 2,
            "source": "source_node",
            "target": "target_node",
            "efficiency_source_target": [95.0, 96.0],
            "efficiency_target_source": [94.0, 93.0],
        },
        "expected_outputs": {
            "power_flow_source_target": {"type": "power", "unit": "kW", "values": (1.0, 2.0)},
            "power_flow_target_source": {"type": "power", "unit": "kW", "values": (0.5, 1.5)},
        },
    },
]

INVALID_CASES: list[dict[str, Any]] = []
