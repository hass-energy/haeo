"""Test data for Amber Electric forecast sensors."""

from datetime import UTC, datetime
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
    {
        "entity_id": "sensor.amber_datetime_objects",
        "state": "0.13",
        "attributes": {
            "forecasts": [
                {
                    "per_kwh": 0.13,
                    "start_time": datetime(2025, 10, 5, 11, 0, 0, tzinfo=UTC),
                },
                {
                    "per_kwh": 0.16,
                    "start_time": datetime(2025, 10, 5, 11, 30, 0, tzinfo=UTC),
                },
            ]
        },
        "expected_format": "amberelectric",
        "expected_count": 2,
        "description": "Amber forecast with datetime objects instead of strings",
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
        "expected_format": None,
        "expected_count": 0,
        "description": "Amber forecast with invalid/missing fields",
    },
    {
        "entity_id": "sensor.amber_bad_timestamp",
        "state": "0.13",
        "attributes": {"forecasts": [{"start_time": "not a timestamp", "per_kwh": 0.1}]},
        "expected_format": None,
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
    {
        "entity_id": "sensor.empty_forecasts",
        "state": "0",
        "attributes": {"forecasts": []},
        "expected_format": None,
        "description": "Amber sensor with empty forecasts list",
    },
    {
        "entity_id": "sensor.amber_mixed_valid_invalid",
        "state": "0.13",
        "attributes": {
            "forecasts": [
                {
                    "per_kwh": 0.2,
                    "start_time": "2025-10-05T11:10:00+00:00",
                },
                {
                    "per_kwh": "oops",
                    "start_time": "2025-10-05T11:15:00+00:00",
                },
            ]
        },
        "expected_format": None,
        "expected_count": 0,
        "description": "Amber forecast containing both valid and invalid rows",
    },
    {
        "entity_id": "sensor.amber_non_dict_entry",
        "state": "0.13",
        "attributes": {
            "forecasts": [
                {
                    "per_kwh": 0.18,
                    "start_time": "2025-10-05T11:20:00+00:00",
                },
                "not-a-dict",
            ]
        },
        "expected_format": None,
        "expected_count": 0,
        "description": "Amber forecast containing a non-mapping item",
    },
]
