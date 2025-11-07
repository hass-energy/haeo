"""Test data for node element configuration."""

from typing import Any

# Valid node configurations
VALID: list[dict[str, Any]] = [
    {
        "data": {
            "element_type": "node",
            "name": "Junction Node",
        },
        "description": "Simple junction node",
    },
    {
        "data": {
            "element_type": "node",
            "name": "Main Bus",
        },
        "description": "Main electrical bus node",
    },
    {
        "data": {
            "element_type": "node",
            "name": "Inverter Input",
        },
        "description": "Inverter input connection node",
    },
]

# Invalid node configurations
INVALID: list[dict[str, Any]] = [
    {
        "data": {
            "element_type": "node",
        },
        "description": "Node missing required name field",
    },
    {
        "data": {
            "element_type": "node",
            "name": "",
        },
        "description": "Node with empty name",
    },
]
