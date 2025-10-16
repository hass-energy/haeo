"""Test data and validation for node flow configuration."""

# Test data for node flow
VALID_DATA = [
    {
        "description": "Basic node configuration",
        "config": {"name_value": "Test Node"},
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {"name_value": ""},
        "error": "cannot be empty",
    },
]
