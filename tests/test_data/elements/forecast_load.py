"""Test data for forecast load element configuration."""

from typing import Any

# Valid forecast load configurations
VALID: list[dict[str, Any]] = [
    {
        "data": {
            "element_type": "forecast_load",
            "name": "House Load",
            "forecast": ["sensor.load_forecast"],
        },
        "expected_description": "Forecast Load",
        "description": "Forecast load with forecast sensor",
    },
    {
        "data": {
            "element_type": "forecast_load",
            "name": "Multi Source Load",
            "forecast": ["sensor.circuit_1", "sensor.circuit_2", "sensor.circuit_3"],
        },
        "expected_description": "Forecast Load",
        "description": "Forecast load with multiple forecast sensors",
    },
]

# Invalid forecast load configurations
INVALID: list[dict[str, Any]] = [
    {
        "data": {
            "element_type": "forecast_load",
            "name": "Missing Forecast",
        },
        "description": "Forecast load missing required forecast field",
    },
    {
        "data": {
            "element_type": "forecast_load",
            "name": "Invalid Forecast Type",
            "forecast": 1.5,
        },
        "description": "Forecast load with number forecast instead of list",
    },
]
