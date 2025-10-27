"""Test data for constant load element configuration."""

from typing import Any

# Valid constant load configurations
VALID: list[dict[str, Any]] = [
    {
        "data": {
            "element_type": "constant_load",
            "name": "Base Load",
            "power": 1.5,
        },
        "expected_description": "Constant Load 1.5kW",
        "description": "Constant load with fixed power",
    },
    {
        "data": {
            "element_type": "constant_load",
            "name": "Small Appliance",
            "power": 0.5,
        },
        "expected_description": "Constant Load 0.5kW",
        "description": "Small constant load",
    },
    {
        "data": {
            "element_type": "constant_load",
            "name": "Large Load",
            "power": 10.0,
        },
        "expected_description": "Constant Load 10.0kW",
        "description": "Large constant load",
    },
    {
        "data": {
            "element_type": "constant_load",
            "name": "Very Small Load",
            "power": 0.001,
        },
        "expected_description": "Constant Load 0.0kW",
        "description": "Very small constant load",
    },
]

# Invalid constant load configurations
INVALID: list[dict[str, Any]] = [
    {
        "data": {
            "element_type": "constant_load",
            "name": "Missing Power",
        },
        "description": "Constant load missing required power field",
    },
    {
        "data": {
            "element_type": "constant_load",
            "name": "Negative Power",
            "power": -5.0,
        },
        "description": "Constant load with negative power",
    },
    {
        "data": {
            "element_type": "constant_load",
            "name": "Invalid Power Type",
            "power": "1.5kW",
        },
        "description": "Constant load with string power instead of number",
    },
    {
        "data": {
            "element_type": "constant_load",
            "name": "Zero Load",
            "power": 0.0,
        },
        "description": "Constant load with zero power",
    },
]
