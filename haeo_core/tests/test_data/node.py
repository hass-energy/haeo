"""Test data and factories for Node element."""

from haeo_core.model.node import Node

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
        "description": "Node with multiple periods",
        "factory": Node,
        "data": {
            "name": "hub_node",
            "period": 1,
            "n_periods": 24,
        },
        "expected_outputs": {},
    },
]

INVALID_CASES: list[ElementTestCase] = []
