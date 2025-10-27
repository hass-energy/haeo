"""Test data for AEMO NEM forecast sensors."""

from typing import Any

# Valid AEMO sensor configurations
VALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.aemo_forecast",
        "state": "0.0748",
        "attributes": {
            "forecast": [
                {
                    "start_time": "2025-10-05T21:00:00+10:00",
                    "end_time": "2025-10-05T21:30:00+10:00",
                    "price": 0.0748,
                }
            ]
        },
        "expected_format": "aemo_nem",
        "expected_count": 1,
        "description": "Single AEMO forecast entry",
    },
    {
        "entity_id": "sensor.aemo_multi_forecast",
        "state": "0.0748",
        "attributes": {
            "forecast": [
                {
                    "start_time": "2025-10-05T21:00:00+10:00",
                    "end_time": "2025-10-05T21:30:00+10:00",
                    "price": 0.0748,
                },
                {
                    "start_time": "2025-10-05T21:30:00+10:00",
                    "end_time": "2025-10-05T22:00:00+10:00",
                    "price": 0.0823,
                },
            ]
        },
        "expected_format": "aemo_nem",
        "expected_count": 2,
        "description": "Multiple AEMO forecast entries",
    },
]

# Invalid AEMO sensor configurations
INVALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.aemo_no_forecast",
        "state": "0",
        "attributes": {},
        "expected_format": None,
        "description": "AEMO sensor missing forecast attribute",
    },
    {
        "entity_id": "sensor.aemo_bad_forecast",
        "state": "0",
        "attributes": {"forecast": "not a list"},
        "expected_format": None,
        "description": "AEMO sensor with forecast not being a list",
    },
    {
        "entity_id": "sensor.aemo_empty_forecast",
        "state": "0",
        "attributes": {"forecast": []},
        "expected_format": None,
        "description": "AEMO sensor with empty forecast list",
    },
    {
        "entity_id": "sensor.aemo_invalid_items",
        "state": "0",
        "attributes": {"forecast": ["string", 123, None, {"start_time": "2024-01-01T00:00:00Z", "price": 0.1}]},
        "expected_format": "aemo_nem",
        "expected_count": 1,
        "description": "AEMO sensor with non-dict items (only valid item parsed)",
    },
    {
        "entity_id": "sensor.aemo_missing_fields",
        "state": "0",
        "attributes": {
            "forecast": [
                {"start_time": "2024-01-01T00:00:00Z"},  # Missing price
                {"price": 0.1},  # Missing start_time
                {"start_time": "2024-01-01T00:00:00Z", "price": 0.1},  # Valid
            ]
        },
        "expected_format": "aemo_nem",
        "expected_count": 1,
        "description": "AEMO sensor with items missing required fields",
    },
    {
        "entity_id": "sensor.aemo_bad_timestamp",
        "state": "0",
        "attributes": {"forecast": [{"start_time": "not a timestamp", "price": 0.1}]},
        "expected_format": "aemo_nem",
        "expected_count": 0,
        "description": "AEMO sensor with invalid timestamp",
    },
]
