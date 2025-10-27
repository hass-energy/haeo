"""Test data for Amber Electric forecast sensors."""

from typing import Any

# Valid Amber sensor configurations
VALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.amber_forecast",
        "state": "0.13",
        "attributes": {
            "forecasts": [
                {
                    "duration": 5,
                    "date": "2025-10-05",
                    "per_kwh": 0.13,
                    "start_time": "2025-10-05T11:00:01+00:00",
                    "end_time": "2025-10-05T11:05:00+00:00",
                }
            ]
        },
        "expected_format": "amberelectric",
        "expected_count": 1,
        "description": "Single Amber forecast entry",
    },
    {
        "entity_id": "sensor.amber_multi_forecast",
        "state": "0.13",
        "attributes": {
            "forecasts": [
                {
                    "duration": 5,
                    "per_kwh": 0.13,
                    "start_time": "2025-10-05T11:00:01+00:00",
                    "end_time": "2025-10-05T11:05:00+00:00",
                },
                {
                    "duration": 5,
                    "per_kwh": 0.15,
                    "start_time": "2025-10-05T11:05:01+00:00",
                    "end_time": "2025-10-05T11:10:00+00:00",
                },
            ]
        },
        "expected_format": "amberelectric",
        "expected_count": 2,
        "description": "Multiple Amber forecast entries",
    },
    {
        "entity_id": "sensor.amber_forecast_tz",
        "state": "0.13",
        "attributes": {
            "forecasts": [
                {
                    "per_kwh": 0.13,
                    "start_time": "2025-10-05T21:00:01+10:00",
                }
            ]
        },
        "expected_format": "amberelectric",
        "expected_count": 1,
        "description": "Amber forecast with timezone conversion",
    },
]

# Invalid Amber sensor configurations
INVALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.amber_invalid",
        "state": "0.13",
        "attributes": {
            "forecasts": [
                {
                    "per_kwh": 0.13,
                    # Missing start_time
                },
                {
                    "start_time": "2025-10-05T11:00:01+00:00",
                    # Missing per_kwh
                },
                {
                    "per_kwh": "invalid",
                    "start_time": "2025-10-05T11:00:01+00:00",
                },
            ]
        },
        "expected_format": "amberelectric",
        "expected_count": 0,
        "description": "Amber forecast with invalid/missing fields",
    },
    {
        "entity_id": "sensor.amber_bad_timestamp",
        "state": "0.13",
        "attributes": {"forecasts": [{"start_time": "not a timestamp", "per_kwh": 0.1}]},
        "expected_format": "amberelectric",
        "expected_count": 0,
        "description": "Amber forecast with invalid timestamp",
    },
    {
        "entity_id": "sensor.no_forecasts",
        "state": "0",
        "attributes": {},
        "expected_format": None,
        "description": "Amber sensor missing forecasts attribute",
    },
    {
        "entity_id": "sensor.bad_forecasts",
        "state": "0",
        "attributes": {"forecasts": "not a list"},
        "expected_format": None,
        "description": "Amber sensor with forecasts not being a list",
    },
]
