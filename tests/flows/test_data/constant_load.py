"""Test data and validation for constant load flow configuration."""


# Test data for load constant flow
VALID_DATA = [
    {
        "description": "Fixed load configuration",
        "config": {
            "name_value": "Test Load",
            "power_value": 1500,
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {"name_value": "", "power_value": 1500},
        "error": "cannot be empty",
    },
    {
        "description": "Negative power should fail validation",
        "config": {"name_value": "Test Load", "power_value": -500},
        "error": "value must be positive",
    },
]
