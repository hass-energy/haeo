"""Test data for Amber2MQTT forecast sensors."""

from datetime import UTC, datetime
from typing import Any

# Valid Amber2MQTT sensor configurations
VALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.amber2mqtt_general_forecast",
        "state": "0.13",
        "attributes": {
            "Forecasts": [
                {
                    "duration": 5,
                    "date": "2025-10-05",
                    "per_kwh": 0.13,
                    "start_time": "2025-10-05T11:00:01+00:00",
                    "end_time": "2025-10-05T11:05:00+00:00",
                }
            ]
        },
        "expected_format": "amber2mqtt",
        "expected_count": 2,
        "description": "Single Amber2MQTT forecast entry (consumption)",
    },
    {
        "entity_id": "sensor.amber2mqtt_multi_forecast",
        "state": "0.13",
        "attributes": {
            "Forecasts": [
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
        "expected_format": "amber2mqtt",
        "expected_count": 4,
        "description": "Multiple Amber2MQTT forecast entries",
    },
    {
        "entity_id": "sensor.amber2mqtt_feed_in_forecast",
        "state": "-0.05",
        "attributes": {
            "Forecasts": [
                {
                    "per_kwh": 0.05,
                    "start_time": "2025-10-05T11:00:01+00:00",
                    "end_time": "2025-10-05T11:05:00+00:00",
                }
            ]
        },
        "expected_format": "amber2mqtt",
        "expected_count": 2,
        "description": "Amber2MQTT feed-in sensor (per_kwh should be negated)",
    },
    {
        "entity_id": "sensor.amber2mqtt_feedin_tariff",
        "state": "-0.08",
        "attributes": {
            "Forecasts": [
                {
                    "per_kwh": 0.08,
                    "start_time": "2025-10-05T11:00:01+00:00",
                    "end_time": "2025-10-05T11:05:00+00:00",
                }
            ]
        },
        "expected_format": "amber2mqtt",
        "expected_count": 2,
        "description": "Amber2MQTT feedin sensor (alternative naming, per_kwh should be negated)",
    },
    {
        "entity_id": "sensor.amber2mqtt_datetime_objects",
        "state": "0.13",
        "attributes": {
            "Forecasts": [
                {
                    "per_kwh": 0.13,
                    "start_time": datetime(2025, 10, 5, 11, 0, 0, tzinfo=UTC),
                    "end_time": datetime(2025, 10, 5, 11, 5, 0, tzinfo=UTC),
                },
                {
                    "per_kwh": 0.16,
                    "start_time": datetime(2025, 10, 5, 11, 30, 0, tzinfo=UTC),
                    "end_time": datetime(2025, 10, 5, 11, 35, 0, tzinfo=UTC),
                },
            ]
        },
        "expected_format": "amber2mqtt",
        "expected_count": 4,
        "description": "Amber2MQTT forecast with datetime objects instead of strings",
    },
]

# Invalid Amber2MQTT sensor configurations
INVALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.amber2mqtt_invalid",
        "state": "0.13",
        "attributes": {
            "Forecasts": [
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
        "description": "Amber2MQTT forecast with invalid/missing fields",
    },
    {
        "entity_id": "sensor.amber2mqtt_missing_end_time",
        "state": "0.13",
        "attributes": {
            "Forecasts": [
                {
                    "start_time": "2025-10-05T11:00:01+00:00",
                    "per_kwh": 0.13,
                    # Missing end_time
                }
            ]
        },
        "expected_format": None,
        "expected_count": 0,
        "description": "Amber2MQTT forecast missing end_time",
    },
    {
        "entity_id": "sensor.amber2mqtt_bad_timestamp",
        "state": "0.13",
        "attributes": {"Forecasts": [{"start_time": "not a timestamp", "end_time": "2025-10-05T11:05:00+00:00", "per_kwh": 0.1}]},
        "expected_format": None,
        "expected_count": 0,
        "description": "Amber2MQTT forecast with invalid timestamp",
    },
    {
        "entity_id": "sensor.amber2mqtt_no_forecasts",
        "state": "0",
        "attributes": {},
        "expected_format": None,
        "description": "Amber2MQTT sensor missing Forecasts attribute",
    },
    {
        "entity_id": "sensor.amber2mqtt_bad_forecasts",
        "state": "0",
        "attributes": {"Forecasts": "not a list"},
        "expected_format": None,
        "description": "Amber2MQTT sensor with Forecasts not being a list",
    },
    {
        "entity_id": "sensor.amber2mqtt_empty_forecasts",
        "state": "0",
        "attributes": {"Forecasts": []},
        "expected_format": None,
        "description": "Amber2MQTT sensor with empty Forecasts list",
    },
]
