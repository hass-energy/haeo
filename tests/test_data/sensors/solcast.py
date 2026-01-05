"""Test data for Solcast Solar forecast sensors."""

from datetime import UTC, datetime
from typing import Any

# Valid Solcast sensor configurations
# Solcast returns power in kW (no conversion needed)
# Timestamps: 2025-10-06T00:00:00+11:00 = 2025-10-05T13:00:00Z = 1759669200
#             2025-10-06T00:15:00+11:00 = 2025-10-05T13:15:00Z = 1759670100
#             2025-10-06T00:30:00+11:00 = 2025-10-05T13:30:00Z = 1759671000
#             2025-10-06T01:00:00+11:00 = 2025-10-05T14:00:00Z = 1759672800
# For UTC times: 2025-10-06T00:00:00Z = 1759708800
#                2025-10-06T00:30:00Z = 1759710600
#                2025-10-06T01:00:00Z = 1759712400
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
        "expected_unit": "kW",
        "expected_data": [
            (1759669200.0, 0.0),
        ],
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
        "expected_unit": "kW",
        "expected_data": [
            (1759669200.0, 0.0),
            (1759670100.0, 10.0),
        ],
        "description": "Multiple Solcast forecast entries",
    },
    {
        "entity_id": "sensor.solcast_datetime_objects",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {
                    "period_start": datetime(2025, 10, 6, 0, 0, 0, tzinfo=UTC),
                    "pv_estimate": 5,
                },
                {
                    "period_start": datetime(2025, 10, 6, 0, 30, 0, tzinfo=UTC),
                    "pv_estimate": 15,
                },
            ]
        },
        "expected_format": "solcast_solar",
        "expected_count": 2,
        "expected_unit": "kW",
        # UTC times: 2025-10-06T00:00:00Z = 1759708800
        #            2025-10-06T00:30:00Z = 1759710600
        "expected_data": [
            (1759708800.0, 5.0),
            (1759710600.0, 15.0),
        ],
        "description": "Solcast forecast with datetime objects instead of strings",
    },
    {
        "entity_id": "sensor.solcast_mixed_datetime_types",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {
                    "period_start": "2025-10-06T00:00:00+11:00",
                    "pv_estimate": 3,
                },
                {
                    "period_start": datetime(2025, 10, 6, 1, 0, 0, tzinfo=UTC),
                    "pv_estimate": 8,
                },
            ]
        },
        "expected_format": "solcast_solar",
        "expected_count": 2,
        "expected_unit": "kW",
        # 2025-10-06T00:00:00+11:00 = 1759669200
        # 2025-10-06T01:00:00Z = 1759712400
        "expected_data": [
            (1759669200.0, 3.0),
            (1759712400.0, 8.0),
        ],
        "description": "Solcast forecast with mixed string and datetime object timestamps",
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
        "entity_id": "sensor.solcast_empty_detailed_forecast",
        "state": "0",
        "attributes": {"detailedForecast": []},
        "expected_format": None,
        "description": "Solcast sensor with empty detailedForecast list",
    },
    {
        "entity_id": "sensor.solcast_bad_timestamp",
        "state": "0",
        "attributes": {"detailedForecast": [{"period_start": "not a timestamp", "pv_estimate": 100}]},
        "expected_format": None,
        "expected_count": 0,
        "description": "Solcast sensor with invalid timestamp",
    },
    {
        "entity_id": "sensor.solcast_mixed_valid_invalid",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {
                    "period_start": "2025-10-06T00:00:00+11:00",
                    "pv_estimate": 0,
                },
                {
                    "period_start": "corrupt",
                    "pv_estimate": 5,
                },
            ]
        },
        "expected_format": None,
        "expected_count": 0,
        "description": "Solcast forecast containing both valid and invalid rows",
    },
    {
        "entity_id": "sensor.solcast_non_dict_entry",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {
                    "period_start": "2025-10-06T00:30:00+11:00",
                    "pv_estimate": 8,
                },
                "not-a-dict",
            ]
        },
        "expected_format": None,
        "expected_count": 0,
        "description": "Solcast forecast containing a non-mapping item",
    },
    {
        "entity_id": "sensor.solcast_missing_fields",
        "state": "0",
        "attributes": {
            "detailedForecast": [
                {
                    "period_start": "2025-10-06T00:45:00+11:00",
                },
                {
                    "pv_estimate": 12,
                },
            ]
        },
        "expected_format": None,
        "expected_count": 0,
        "description": "Solcast forecast missing required fields",
    },
]
