"""Test data for connection element configuration."""

from typing import Any

# Valid connection configurations
VALID: list[dict[str, Any]] = [
    {
        "data": {
            "element_type": "connection",
            "name": "Bidirectional Connection",
            "source": "battery",
            "target": "grid",
            "min_power": 2.0,
            "max_power": 4.0,
        },
        "expected_description": "Connection 2.0kW to 4.0kW",
        "description": "Connection with both min and max power",
    },
    {
        "data": {
            "element_type": "connection",
            "name": "Min Only Connection",
            "source": "solar",
            "target": "inverter",
            "min_power": 2.0,
        },
        "expected_description": "Connection (min 2.0kW)",
        "description": "Connection with only minimum power",
    },
    {
        "data": {
            "element_type": "connection",
            "name": "Max Only Connection",
            "source": "inverter",
            "target": "house",
            "max_power": 10.0,
        },
        "expected_description": "Connection (max 10.0kW)",
        "description": "Connection with only maximum power",
    },
    {
        "data": {
            "element_type": "connection",
            "name": "Unconstrained Connection",
            "source": "node_a",
            "target": "node_b",
        },
        "expected_description": "Connection",
        "description": "Connection with no power constraints",
    },
]

# Invalid connection configurations
INVALID: list[dict[str, Any]] = [
    {
        "data": {
            "element_type": "connection",
            "name": "Missing Source",
            "target": "grid",
            "max_power": 5.0,
        },
        "description": "Connection missing required source field",
    },
    {
        "data": {
            "element_type": "connection",
            "name": "Missing Target",
            "source": "battery",
            "max_power": 5.0,
        },
        "description": "Connection missing required target field",
    },
    {
        "data": {
            "element_type": "connection",
            "name": "Negative Power",
            "source": "a",
            "target": "b",
            "max_power": -5.0,
        },
        "description": "Connection with negative max power",
    },
    {
        "data": {
            "element_type": "connection",
            "name": "Min Greater Than Max",
            "source": "a",
            "target": "b",
            "min_power": 10.0,
            "max_power": 5.0,
        },
        "description": "Connection with min_power > max_power",
    },
    {
        "data": {
            "element_type": "connection",
            "name": "Zero Power Connection",
            "source": "a",
            "target": "b",
            "min_power": 0.0,
            "max_power": 0.0,
        },
        "description": "Connection with zero power limits",
    },
    {
        "data": {
            "element_type": "connection",
            "name": "Same Source Target",
            "source": "node",
            "target": "node",
            "max_power": 5.0,
        },
        "description": "Connection with same source and target (should be caught by validation)",
    },
]
