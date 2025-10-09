"""Test data and validation for forecast load flow configuration."""


# Test data for load forecast flow
VALID_DATA = [
    {
        "description": "Variable load with forecast sensors",
        "config": {
            "name_value": "Forecast Load",
            "forecast_value": ["sensor.forecast1", "sensor.forecast2"],
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {"name_value": "", "forecast_value": ["sensor.forecast1"]},
        "error": "cannot be empty",
    },
    {
        "description": "Invalid forecast sensors should fail validation",
        "config": {"name_value": "Test Load", "forecast_value": "not_a_list"},
        "error": "value should be a list",
    },
]
