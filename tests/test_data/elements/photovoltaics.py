"""Test data for photovoltaics element configuration."""

from typing import Any

# Valid photovoltaics configurations
VALID: list[dict[str, Any]] = [
    {
        "data": {
            "element_type": "photovoltaics",
            "name": "Rooftop Solar",
            "forecast": ["sensor.solcast_forecast"],
        },
        "description": "Solar with forecast",
    },
    {
        "data": {
            "element_type": "photovoltaics",
            "name": "Solar with Price",
            "forecast": ["sensor.solcast_forecast"],
            "price_production": 0.12,
        },
        "description": "Solar with forecast and price_production",
    },
    {
        "data": {
            "element_type": "photovoltaics",
            "name": "Solar with Curtailment",
            "forecast": ["sensor.solcast_forecast"],
            "curtailment": True,
        },
        "description": "Solar with curtailment enabled",
    },
]

# Invalid photovoltaics configurations
INVALID: list[dict[str, Any]] = [
    {
        "data": {
            "element_type": "photovoltaics",
            "name": "Missing Forecast",
        },
        "description": "Photovoltaics missing required forecast field",
    },
    {
        "data": {
            "element_type": "photovoltaics",
            "name": "Invalid Forecast Type",
            "forecast": "sensor.solar_forecast",
        },
        "description": "Photovoltaics with incorrect forecast type (should be list)",
    },
]
