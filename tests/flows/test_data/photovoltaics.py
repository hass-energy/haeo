"""Test data and validation for photovoltaics flow configuration."""

# Test data for photovoltaics flow
VALID_DATA = [
    {
        "description": "Basic photovoltaics configuration",
        "config": {
            "name_value": "Test Photovoltaics",
            "forecast_value": ["sensor.solar_power"],
            "curtailment_value": False,
        },
    },
    {
        "description": "Curtailable photovoltaics configuration",
        "config": {
            "name_value": "Curtailable Photovoltaics",
            "forecast_value": ["sensor.solar_power"],
            "curtailment_value": True,
            "price_production_value": 0.03,
        },
    },
    {
        "description": "Photovoltaics with forecast sensors",
        "config": {
            "name_value": "Solar Photovoltaics",
            "forecast_value": ["sensor.solar_power"],
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
