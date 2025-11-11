"""Test data and factories for ForecastLoad element."""

from typing import Any

from custom_components.haeo.model.forecast_load import ForecastLoad


def create(data: dict[str, Any]) -> ForecastLoad:
    """Create a test ForecastLoad instance."""
    return ForecastLoad(**data)


VALID_CASES = [
    {
        "description": "Forecast load with varying consumption",
        "factory": create,
        "data": {
            "name": "forecast_load",
            "period": 1.0,
            "n_periods": 3,
            "forecast": [1.0, 1.5, 2.0],
        },
        "expected_outputs": {
            "power_consumed": {"type": "power", "unit": "kW", "values": (1.0, 1.5, 2.0)},
        },
    },
]

INVALID_CASES = [
    {
        "description": "Forecast load with forecast length mismatch",
        "element_class": ForecastLoad,
        "data": {
            "name": "forecast_load",
            "period": 1.0,
            "n_periods": 3,
            "forecast": [1.0, 1.5],  # Only 2 instead of 3
        },
        "expected_error": r"forecast length \(2\) must match n_periods \(3\)",
    },
]
