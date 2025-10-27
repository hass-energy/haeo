"""Test data for Solcast Solar forecast sensors."""

from typing import Any

# Valid Solcast sensor configurations
VALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.solcast_forecast",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {
                    "period_start": "2025-10-06T00:00:00+11:00",
                    "pv_estimate": 0,
                }
            ]
        },
        "expected_format": "solcast_solar",
        "expected_count": 1,
        "description": "Single Solcast forecast entry",
    },
    {
        "entity_id": "sensor.solcast_multi_forecast",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {
                    "period_start": "2025-10-06T00:00:00+11:00",
                    "pv_estimate": 0,
                },
                {
                    "period_start": "2025-10-06T00:15:00+11:00",
                    "pv_estimate": 10,
                },
            ]
        },
        "expected_format": "solcast_solar",
        "expected_count": 2,
        "description": "Multiple Solcast forecast entries",
    },
]

# Invalid Solcast sensor configurations
INVALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.solcast_no_detailed_forecast",
        "state": "0",
        "attributes": {},
        "expected_format": None,
        "description": "Solcast sensor missing detailedForecast attribute",
    },
    {
        "entity_id": "sensor.solcast_bad_detailed_forecast",
        "state": "0",
        "attributes": {"detailedForecast": "not a list"},
        "expected_format": None,
        "description": "Solcast sensor with detailedForecast not being a list",
    },
    {
        "entity_id": "sensor.solcast_bad_timestamp",
        "state": "0",
        "attributes": {"detailedForecast": [{"period_start": "not a timestamp", "pv_estimate": 100}]},
        "expected_format": "solcast_solar",
        "expected_count": 0,
        "description": "Solcast sensor with invalid timestamp",
    },
]
