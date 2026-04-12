"""Test data for Nordpool energy pricing forecast sensors."""

from typing import Any

VALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.nordpool_kwh_eur",
        "state": "0.093",
        "attributes": {
            "currency": "EUR",
            "raw_today": [
                {
                    "start": "2025-10-05T00:00:00+02:00",
                    "end": "2025-10-05T01:00:00+02:00",
                    "value": 0.10,
                },
                {
                    "start": "2025-10-05T01:00:00+02:00",
                    "end": "2025-10-05T02:00:00+02:00",
                    "value": 0.08,
                },
            ],
            "raw_tomorrow": [],
        },
        "expected_format": "nordpool",
        "expected_unit": "EUR/kWh",
        "expected_data": [
            (1759615200.0, 0.10),
            (1759618800.0, 0.10),
            (1759618800.0, 0.08),
            (1759622400.0, 0.08),
        ],
        "description": "Nordpool sensor with two hourly entries",
    },
    {
        "entity_id": "sensor.nordpool_kwh_eur_15min",
        "state": "0.25",
        "attributes": {
            "currency": "EUR",
            "raw_today": [
                {
                    "start": "2025-10-05T00:00:00+02:00",
                    "end": "2025-10-05T00:15:00+02:00",
                    "value": 0.25,
                },
                {
                    "start": "2025-10-05T00:15:00+02:00",
                    "end": "2025-10-05T00:30:00+02:00",
                    "value": 0.30,
                },
            ],
            "raw_tomorrow": [
                {
                    "start": "2025-10-06T00:00:00+02:00",
                    "end": "2025-10-06T00:15:00+02:00",
                    "value": 0.12,
                },
            ],
        },
        "expected_format": "nordpool",
        "expected_unit": "EUR/kWh",
        "expected_data": [
            (1759615200.0, 0.25),
            (1759616100.0, 0.25),
            (1759616100.0, 0.30),
            (1759617000.0, 0.30),
            (1759701600.0, 0.12),
            (1759702500.0, 0.12),
        ],
        "description": "Nordpool sensor with 15-minute intervals and tomorrow data",
    },
    {
        "entity_id": "sensor.nordpool_kwh_nok",
        "state": "1.25",
        "attributes": {
            "currency": "NOK",
            "raw_today": [
                {
                    "start": "2025-10-05T00:00:00+02:00",
                    "end": "2025-10-05T01:00:00+02:00",
                    "value": 1.25,
                },
            ],
            "raw_tomorrow": [],
        },
        "expected_format": "nordpool",
        "expected_unit": "NOK/kWh",
        "expected_data": [
            (1759615200.0, 1.25),
            (1759618800.0, 1.25),
        ],
        "description": "Nordpool sensor with NOK currency",
    },
]

# Invalid Nordpool sensor configurations
INVALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.nordpool_no_raw_today",
        "state": "0.10",
        "attributes": {
            "currency": "EUR",
            "today": [0.10, 0.08],
        },
        "expected_format": None,
        "description": "Nordpool sensor missing raw_today attribute",
    },
    {
        "entity_id": "sensor.nordpool_empty_raw_today",
        "state": "0.10",
        "attributes": {
            "currency": "EUR",
            "raw_today": [],
        },
        "expected_format": None,
        "description": "Nordpool sensor with empty raw_today list",
    },
    {
        "entity_id": "sensor.nordpool_bad_raw_today",
        "state": "0.10",
        "attributes": {
            "currency": "EUR",
            "raw_today": "not a list",
        },
        "expected_format": None,
        "description": "Nordpool sensor with raw_today not being a list",
    },
    {
        "entity_id": "sensor.nordpool_missing_fields",
        "state": "0.10",
        "attributes": {
            "currency": "EUR",
            "raw_today": [{"start": "2025-10-05T00:00:00+02:00", "value": 0.10}],
        },
        "expected_format": None,
        "description": "Nordpool sensor with entry missing end field",
    },
    {
        "entity_id": "sensor.nordpool_invalid_value",
        "state": "0.10",
        "attributes": {
            "currency": "EUR",
            "raw_today": [
                {
                    "start": "2025-10-05T00:00:00+02:00",
                    "end": "2025-10-05T01:00:00+02:00",
                    "value": "not_a_number",
                },
            ],
        },
        "expected_format": None,
        "description": "Nordpool sensor with non-numeric value",
    },
]
