"""Test data for Amber2MQTT forecast sensors."""

from datetime import UTC, datetime
from typing import Any

import numpy as np

VALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.amber2mqtt_general_forecast",
        "state": "0.13",
        "attributes": {
            "Forecasts": [
                {
                    "duration": 5,
                    "date": "2025-10-05",
                    "advanced_price_predicted": 0.13,
                    "start_time": "2025-10-05T11:00:01+00:00",
                    "end_time": "2025-10-05T11:05:00+00:00",
                }
            ]
        },
        "expected_format": "amber2mqtt",
        "expected_unit": "$/kWh",
        "expected_data": [(1759662000.0, 0.13), (1759662300.0, 0.13)],
        "description": "Single Amber2MQTT forecast entry (consumption)",
    },
    {
        "entity_id": "sensor.amber2mqtt_multi_forecast",
        "state": "0.13",
        "attributes": {
            "Forecasts": [
                {
                    "duration": 5,
                    "advanced_price_predicted": 0.13,
                    "start_time": "2025-10-05T11:00:01+00:00",
                    "end_time": "2025-10-05T11:05:00+00:00",
                },
                {
                    "duration": 5,
                    "advanced_price_predicted": 0.15,
                    "start_time": "2025-10-05T11:05:01+00:00",
                    "end_time": "2025-10-05T11:10:00+00:00",
                },
            ]
        },
        "expected_format": "amber2mqtt",
        "expected_unit": "$/kWh",
        "expected_data": [(1759662000.0, 0.13), (np.nextafter(1759662300.0, -np.inf), 0.13), (1759662300.0, 0.15), (1759662600.0, 0.15)],
        "description": "Multiple Amber2MQTT forecast entries",
    },
    {
        "entity_id": "sensor.amber2mqtt_feed_in_forecast",
        "state": "-0.05",
        "attributes": {
            "channel_type": "feedin",
            "Forecasts": [
                {
                    "advanced_price_predicted": 0.05,
                    "start_time": "2025-10-05T11:00:01+00:00",
                    "end_time": "2025-10-05T11:05:00+00:00",
                }
            ],
        },
        "expected_format": "amber2mqtt",
        "expected_unit": "$/kWh",
        "expected_data": [(1759662000.0, -0.05), (1759662300.0, -0.05)],
        "description": "Amber2MQTT feed-in sensor (advanced_price_predicted should be negated)",
    },
    {
        "entity_id": "sensor.amber2mqtt_feedin_tariff",
        "state": "-0.08",
        "attributes": {
            "channel_type": "feedin",
            "Forecasts": [
                {
                    "advanced_price_predicted": 0.08,
                    "start_time": "2025-10-05T11:00:01+00:00",
                    "end_time": "2025-10-05T11:05:00+00:00",
                }
            ],
        },
        "expected_format": "amber2mqtt",
        "expected_unit": "$/kWh",
        "expected_data": [(1759662000.0, -0.08), (1759662300.0, -0.08)],
        "description": "Amber2MQTT feedin sensor (alternative naming, advanced_price_predicted should be negated)",
    },
    {
        "entity_id": "sensor.amber2mqtt_datetime_objects",
        "state": "0.13",
        "attributes": {
            "Forecasts": [
                {
                    "advanced_price_predicted": 0.13,
                    "start_time": datetime(2025, 10, 5, 11, 0, 0, tzinfo=UTC),
                    "end_time": datetime(2025, 10, 5, 11, 5, 0, tzinfo=UTC),
                },
                {
                    "advanced_price_predicted": 0.16,
                    "start_time": datetime(2025, 10, 5, 11, 30, 0, tzinfo=UTC),
                    "end_time": datetime(2025, 10, 5, 11, 35, 0, tzinfo=UTC),
                },
            ]
        },
        "expected_format": "amber2mqtt",
        "expected_unit": "$/kWh",
        "expected_data": [(1759662000.0, 0.13), (1759662300.0, 0.13), (1759663800.0, 0.16), (1759664100.0, 0.16)],
        "description": "Amber2MQTT forecast with datetime objects instead of strings",
    },
]

INVALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.amber2mqtt_invalid",
        "state": "0.13",
        "attributes": {
            "Forecasts": [
                {"advanced_price_predicted": 0.13},
                {"start_time": "2025-10-05T11:00:01+00:00"},
                {"advanced_price_predicted": "invalid", "start_time": "2025-10-05T11:00:01+00:00"},
            ]
        },
        "expected_format": None,
        "description": "Amber2MQTT forecast with invalid/missing fields",
    },
    {
        "entity_id": "sensor.amber2mqtt_missing_end_time",
        "state": "0.13",
        "attributes": {"Forecasts": [{"start_time": "2025-10-05T11:00:01+00:00", "advanced_price_predicted": 0.13}]},
        "expected_format": None,
        "description": "Amber2MQTT forecast missing end_time",
    },
    {
        "entity_id": "sensor.amber2mqtt_bad_timestamp",
        "state": "0.13",
        "attributes": {"Forecasts": [{"start_time": "not a timestamp", "end_time": "2025-10-05T11:05:00+00:00", "advanced_price_predicted": 0.1}]},
        "expected_format": None,
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
