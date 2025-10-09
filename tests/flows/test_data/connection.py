"""Test data and validation for connection flow configuration."""

# Test data for connection flow
VALID_DATA = [
    {
        "description": "Basic connection configuration",
        "config": {
            "name_value": "Battery to Grid",
            "source_value": "Battery1",
            "target_value": "Grid1",
        },
    },
    {
        "description": "Connection with power limits",
        "config": {
            "name_value": "Battery to Grid",
            "source_value": "Battery1",
            "target_value": "Grid1",
            "min_power_value": 0.0,
            "max_power_value": 5000.0,
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty source should fail validation",
        "config": {"name_value": "Test Connection", "source_value": "", "target_value": "Grid1"},
        "error": "element name cannot be empty",
    },
    {
        "description": "Empty target should fail validation",
        "config": {"name_value": "Test Connection", "source_value": "Battery1", "target_value": ""},
        "error": "element name cannot be empty",
    },
]
