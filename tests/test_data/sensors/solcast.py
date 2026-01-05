"""Test data for Solcast Solar forecast sensors."""

from datetime import UTC, datetime
from typing import Any

VALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.solcast_forecast",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {"period_start": "2025-10-06T00:00:00+11:00", "pv_estimate": 0}
            ]
        },
        "expected_format": "solcast_solar",
        "expected_unit": "kW",
        "expected_data": [(1759669200.0, 0.0)],
        "description": "Single Solcast forecast entry",
    },
    {
        "entity_id": "sensor.solcast_multi_forecast",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {"period_start": "2025-10-06T00:00:00+11:00", "pv_estimate": 0},
                {"period_start": "2025-10-06T00:15:00+11:00", "pv_estimate": 10},
            ]
        },
        "expected_format": "solcast_solar",
        "expected_unit": "kW",
        "expected_data": [(1759669200.0, 0.0), (1759670100.0, 10.0)],
        "description": "Multiple Solcast forecast entries",
    },
    {
        "entity_id": "sensor.solcast_datetime_objects",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {"period_start": datetime(2025, 10, 6, 0, 0, 0, tzinfo=UTC), "pv_estimate": 5},
                {"period_start": datetime(2025, 10, 6, 0, 30, 0, tzinfo=UTC), "pv_estimate": 15},
            ]
        },
        "expected_format": "solcast_solar",
        "expected_unit": "kW",
        "expected_data": [(1759708800.0, 5.0), (1759710600.0, 15.0)],
        "description": "Solcast forecast with datetime objects instead of strings",
    },
    {
        "entity_id": "sensor.solcast_mixed_datetime_types",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {"period_start": "2025-10-06T00:00:00+11:00", "pv_estimate": 3},
                {"period_start": datetime(2025, 10, 6, 1, 0, 0, tzinfo=UTC), "pv_estimate": 8},
            ]
        },
        "expected_format": "solcast_solar",
        "expected_unit": "kW",
        "expected_data": [(1759669200.0, 3.0), (1759712400.0, 8.0)],
        "description": "Solcast forecast with mixed string and datetime object timestamps",
    },
]

INVALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.solcast_no_forecast",
        "state": "0",
        "attributes": {},
        "expected_format": None,
        "description": "Solcast sensor missing detailedForecast attribute",
    },
    {
        "entity_id": "sensor.solcast_bad_forecast",
        "state": "0",
        "attributes": {"detailedForecast": "not a list"},
        "expected_format": None,
        "description": "Solcast sensor with detailedForecast not being a list",
    },
    {
        "entity_id": "sensor.solcast_empty_forecast",
        "state": "0",
        "attributes": {"detailedForecast": []},
        "expected_format": None,
        "description": "Solcast sensor with empty detailedForecast list",
    },
    {
        "entity_id": "sensor.solcast_bad_timestamp",
        "state": "0",
        "attributes": {
            "detailedForecast": [{"period_start": "not a timestamp", "pv_estimate": 100}]
        },
        "expected_format": None,
        "description": "Solcast sensor with invalid timestamp",
    },
    {
        "entity_id": "sensor.solcast_mixed_valid_invalid",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {"period_start": "2025-10-06T00:00:00+11:00", "pv_estimate": 5},
                {"period_start": "bad", "pv_estimate": 10},
            ]
        },
        "expected_format": None,
        "description": "Solcast forecast containing both valid and invalid rows",
    },
    {
        "entity_id": "sensor.solcast_non_mapping_entry",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {"period_start": "2025-10-06T00:15:00+11:00", "pv_estimate": 7},
                "not-a-dict",
            ]
        },
        "expected_format": None,
        "description": "Solcast forecast containing a non-mapping item",
    },
    {
        "entity_id": "sensor.solcast_missing_fields",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {"period_start": "2025-10-06T00:30:00+11:00"},
                {"pv_estimate": 12},
            ]
        },
        "expected_format": None,
        "description": "Solcast forecast missing required fields",
    },
]
