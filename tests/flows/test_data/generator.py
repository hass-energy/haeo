"""Test data and validation for generator flow configuration."""

# Test data for generator flow
VALID_DATA = [
    {
        "description": "Basic generator configuration",
        "config": {
            "name_value": "Test Generator",
            "forecast_value": ["sensor.generator_power"],
            "curtailment_value": False,
        },
    },
    {
        "description": "Curtailable generator configuration",
        "config": {
            "name_value": "Curtailable Generator",
            "forecast_value": ["sensor.generator_power"],
            "curtailment_value": True,
            "price_production_value": 0.03,
        },
    },
    {
        "description": "Generator with forecast sensors",
        "config": {
            "name_value": "Solar Generator",
            "forecast_value": ["sensor.generator_power"],
            "curtailment_value": True,
            "price_production_value": 0.04,
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {"name_value": "", "forecast_value": ["sensor.test"]},
        "error": "cannot be empty",
    },
    {
        "description": "Invalid forecast sensors should fail validation",
        "config": {"name_value": "Test", "forecast_value": "not_a_list", "curtailment_value": False},
        "error": "value should be a list",
    },
]
