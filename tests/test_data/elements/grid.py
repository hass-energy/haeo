"""Test data for grid element configuration."""

from typing import Any

# Valid grid configurations
VALID: list[dict[str, Any]] = [
    {
        "data": {
            "element_type": "grid",
            "name": "Full Grid",
            "import_price": {
                "live": ["sensor.import_price"],
                "forecast": [],
            },
            "export_price": {
                "live": ["sensor.export_price"],
                "forecast": [],
            },
            "import_limit": 7.0,
            "export_limit": 3.5,
        },
        "expected_description": "Grid Import 7.0kW, Export 3.5kW",
        "description": "Grid with both import and export limits",
    },
    {
        "data": {
            "element_type": "grid",
            "name": "Import Only Grid",
            "import_price": {
                "live": ["sensor.import_price"],
                "forecast": [],
            },
            "export_price": {
                "live": ["sensor.export_price"],
                "forecast": [],
            },
            "import_limit": 7.0,
        },
        "expected_description": "Grid Import 7.0kW",
        "description": "Grid with only import limit",
    },
    {
        "data": {
            "element_type": "grid",
            "name": "Export Only Grid",
            "import_price": {
                "live": ["sensor.import_price"],
                "forecast": [],
            },
            "export_price": {
                "live": ["sensor.export_price"],
                "forecast": [],
            },
            "export_limit": 3.5,
        },
        "expected_description": "Grid Export 3.5kW",
        "description": "Grid with only export limit",
    },
    {
        "data": {
            "element_type": "grid",
            "name": "Unlimited Grid",
            "import_price": {
                "live": ["sensor.import_price"],
                "forecast": [],
            },
            "export_price": {
                "live": ["sensor.export_price"],
                "forecast": [],
            },
        },
        "expected_description": "Grid Connection",
        "description": "Grid with no power limits",
    },
    {
        "data": {
            "element_type": "grid",
            "name": "Export Only Edge Case",
            "import_price": {
                "live": ["sensor.import_price"],
                "forecast": [],
            },
            "export_price": {
                "live": ["sensor.export_price"],
                "forecast": [],
            },
            "export_limit": 5.0,
        },
        "expected_description": "Grid Export 5.0kW",
        "description": "Test export-only grid description",
    },
]

# Invalid grid configurations
INVALID: list[dict[str, Any]] = [
    {
        "data": {
            "element_type": "grid",
            "name": "Negative Import",
            "import_price": {
                "live": ["sensor.import_price"],
                "forecast": [],
            },
            "export_price": {
                "live": ["sensor.export_price"],
                "forecast": [],
            },
            "import_limit": -5.0,
        },
        "description": "Grid with negative import limit",
    },
    {
        "data": {
            "element_type": "grid",
            "name": "Missing Prices",
            "import_limit": 7.0,
            "export_limit": 3.5,
        },
        "description": "Grid missing required price configuration",
    },
    {
        "data": {
            "element_type": "grid",
            "name": "Zero Limits Grid",
            "import_price": {
                "live": ["sensor.import_price"],
                "forecast": [],
            },
            "export_price": {
                "live": ["sensor.export_price"],
                "forecast": [],
            },
            "import_limit": 0.0,
            "export_limit": 0.0,
        },
        "description": "Grid with zero power limits",
    },
]
