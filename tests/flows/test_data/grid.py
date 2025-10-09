"""Test data and validation for grid flow configuration."""


# Test data for grid flow
VALID_DATA = [
    {
        "description": "Basic grid configuration",
        "config": {
            "name_value": "Test Grid",
            "import_limit_value": 5000,
            "export_limit_value": 3000,
            "import_price_live": [],
            "import_price_forecast": [],
            "export_price_live": [],
            "export_price_forecast": [],
        },
    },
    {
        "description": "Grid with sensor-based pricing",
        "config": {
            "name_value": "Smart Grid",
            "import_limit_value": 8000,
            "export_limit_value": 5000,
            "import_price_live": ["sensor.smart_grid_import_price"],
            "import_price_forecast": ["sensor.smart_grid_import_price"],
            "export_price_live": ["sensor.smart_grid_export_price"],
            "export_price_forecast": ["sensor.smart_grid_export_price"],
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {
            "name_value": "",
            "import_limit_value": 5000,
            "import_price_live": [],
            "import_price_forecast": [],
            "export_price_live": [],
            "export_price_forecast": [],
        },
        "error": "cannot be empty",
    },
    {
        "description": "Negative import limit should fail validation",
        "config": {
            "name_value": "Test Grid",
            "import_limit_value": -1000,
            "import_price_live": [],
            "import_price_forecast": [],
            "export_price_live": [],
            "export_price_forecast": [],
        },
        "error": "value must be positive",
    },
]
