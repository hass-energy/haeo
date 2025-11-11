"""Test data and factories for Node element."""

from typing import Any

from custom_components.haeo.model.node import Node


def create(data: dict[str, Any]) -> Node:
    """Create a test Node instance."""
    return Node(**data)


VALID_CASES = [
    {
        "description": "Node with basic configuration",
        "factory": create,
        "data": {
            "name": "node",
            "period": 1,
            "n_periods": 2,
        },
        "expected_outputs": {},
    },
]

INVALID_CASES: list[dict[str, Any]] = []
