"""Test data and validation for net flow configuration."""


# Test data for net flow
VALID_DATA = [
    {
        "description": "Basic net configuration",
        "config": {"name_value": "Test Net"},
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {"name_value": ""},
        "error": "cannot be empty",
    },
]
