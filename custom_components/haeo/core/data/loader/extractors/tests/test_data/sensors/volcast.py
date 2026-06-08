"""Test data for Volcast solar forecast sensors."""

from datetime import UTC, datetime
from typing import Any

VALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.volcast_forecast",
        "state": "0",
        "attributes": {"detailedForecast": [{"period_start": "2026-05-29T00:00:00+10:00", "power_w": 0}]},
        "expected_format": "volcast",
        "expected_unit": "kW",
        "expected_data": [(1779976800.0, 0.0)],
        "description": "Single Volcast forecast entry",
    },
    {
        "entity_id": "sensor.volcast_multi_forecast",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {"period_start": "2026-05-29T00:00:00+10:00", "power_w": 0},
                {"period_start": "2026-05-29T00:05:00+10:00", "power_w": 3500},
            ]
        },
        "expected_format": "volcast",
        "expected_unit": "kW",
        "expected_data": [(1779976800.0, 0.0), (1779977100.0, 3.5)],
        "description": "Multiple Volcast forecast entries",
    },
    {
        "entity_id": "sensor.volcast_datetime_objects",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {"period_start": datetime(2026, 5, 29, 0, 0, 0, tzinfo=UTC), "power_w": 2000},
                {"period_start": datetime(2026, 5, 29, 0, 5, 0, tzinfo=UTC), "power_w": 7500},
            ]
        },
        "expected_format": "volcast",
        "expected_unit": "kW",
        "expected_data": [(1780012800.0, 2.0), (1780013100.0, 7.5)],
        "description": "Volcast forecast with datetime objects instead of strings",
    },
    {
        "entity_id": "sensor.volcast_mixed_datetime_types",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {"period_start": "2026-05-29T00:00:00+10:00", "power_w": 1000},
                {"period_start": datetime(2026, 5, 29, 1, 0, 0, tzinfo=UTC), "power_w": 4000},
            ]
        },
        "expected_format": "volcast",
        "expected_unit": "kW",
        "expected_data": [(1779976800.0, 1.0), (1780016400.0, 4.0)],
        "description": "Volcast forecast with mixed string and datetime object timestamps",
    },
]

INVALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.volcast_no_forecast",
        "state": "0",
        "attributes": {},
        "expected_format": None,
        "description": "Volcast sensor missing detailedForecast attribute",
    },
    {
        "entity_id": "sensor.volcast_bad_forecast",
        "state": "0",
        "attributes": {"detailedForecast": "not a list"},
        "expected_format": None,
        "description": "Volcast sensor with detailedForecast not being a list",
    },
    {
        "entity_id": "sensor.volcast_empty_forecast",
        "state": "0",
        "attributes": {"detailedForecast": []},
        "expected_format": None,
        "description": "Volcast sensor with empty detailedForecast list",
    },
    {
        "entity_id": "sensor.volcast_bad_timestamp",
        "state": "0",
        "attributes": {"detailedForecast": [{"period_start": "not a timestamp", "power_w": 100}]},
        "expected_format": None,
        "description": "Volcast sensor with invalid timestamp",
    },
    {
        "entity_id": "sensor.volcast_missing_power_w",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {"period_start": "2026-05-29T00:00:00+10:00"},
                {"period_start": "2026-05-29T00:05:00+10:00"},
            ]
        },
        "expected_format": None,
        "description": "Volcast sensor missing power_w field",
    },
    {
        "entity_id": "sensor.volcast_non_mapping_entry",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {"period_start": "2026-05-29T00:00:00+10:00", "power_w": 500},
                "not-a-dict",
            ]
        },
        "expected_format": None,
        "description": "Volcast forecast containing a non-mapping item",
    },
    {
        "entity_id": "sensor.volcast_mixed_valid_invalid",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {"period_start": "2026-05-29T00:00:00+10:00", "power_w": 500},
                {"period_start": "bad", "power_w": 1000},
            ]
        },
        "expected_format": None,
        "description": "Volcast forecast containing both valid and invalid rows",
    },
]
