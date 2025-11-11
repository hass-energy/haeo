"""Test data for load element configuration."""

from typing import Any

# Valid load configurations
VALID: list[dict[str, Any]] = [
    {
        "data": {
            "element_type": "load",
            "name": "House Load",
            "forecast": ["sensor.load_forecast"],
        },
        "description": "Load with forecast sensor",
    },
    {
        "data": {
            "element_type": "load",
            "name": "Multi Source Load",
            "forecast": ["sensor.circuit_1", "sensor.circuit_2", "sensor.circuit_3"],
        },
        "description": "Load with multiple forecast sensors",
    },
]

# Invalid load configurations
INVALID: list[dict[str, Any]] = [
    {
        "data": {
            "element_type": "load",
            "name": "Missing Forecast",
        },
        "description": "Load missing required forecast field",
    },
    {
        "data": {
            "element_type": "load",
            "name": "Invalid Forecast Type",
            "forecast": 1.5,
        },
        "description": "Load with number forecast instead of list",
    },
]
