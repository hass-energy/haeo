"""Test data and factories for Node element."""

from custom_components.haeo.model.node import Node

from .element_types import ElementTestCase

VALID_CASES: list[ElementTestCase] = [
    {
        "description": "Node with basic configuration",
        "factory": Node,
        "data": {
            "name": "node",
            "period": 1,
            "n_periods": 2,
        },
        "expected_outputs": {},
    },
    {
        "description": "Node with shadow prices",
        "factory": Node,
        "data": {
            "name": "hub_node",
            "period": 1,
            "n_periods": 3,
        },
        "inputs": {
            "power": [0.0, 0.0, 0.0],  # Balanced power at node
            "input_cost": 0.1,
            "output_cost": 0.1,
        },
        "expected_outputs": {
            "node_power_balance": {"type": "shadow_price", "unit": "$/kW", "values": (0.0, 0.0, 0.0)},
        },
    },
]

INVALID_CASES: list[ElementTestCase] = []
