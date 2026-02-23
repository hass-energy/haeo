"""Test data and factories for Node element."""

import numpy as np

from custom_components.haeo.core.model.elements.node import Node

from .element_types import ElementTestCase

VALID_CASES: list[ElementTestCase] = [
    {
        "description": "Node with basic configuration",
        "factory": Node,
        "data": {
            "name": "node",
            "periods": np.array([1.0] * 2),
        },
        "expected_outputs": {},
    },
    {
        "description": "Node with shadow prices",
        "factory": Node,
        "data": {
            "name": "hub_node",
            "periods": np.array([1.0] * 3),
            "is_source": False,
            "is_sink": False,
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
