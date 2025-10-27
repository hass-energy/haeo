"""Test data for Open-Meteo Solar forecast sensors."""

from typing import Any

# Valid Open-Meteo sensor configurations
VALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.open_meteo_forecast",
        "state": "175",
        "attributes": {
            "watts": {
                "2025-10-06T06:45:00+11:00": 175,
                "2025-10-06T07:00:00+11:00": 200,
            }
        },
        "expected_format": "open_meteo_solar_forecast",
        "expected_count": 2,
        "description": "Open-Meteo forecast with watts dict",
    },
    {
        "entity_id": "sensor.open_meteo_multi_forecast",
        "state": "175",
        "attributes": {
            "watts": {
                "2025-10-06T06:45:00+11:00": 175,
                "2025-10-06T07:00:00+11:00": 200,
            }
        },
        "expected_format": "open_meteo_solar_forecast",
        "expected_count": 2,
        "description": "Multiple Open-Meteo forecast entries",
    },
]

# Invalid Open-Meteo sensor configurations
INVALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.open_meteo_no_watts",
        "state": "0",
        "attributes": {},
        "expected_format": None,
        "description": "Open-Meteo sensor missing watts attribute",
    },
    {
        "entity_id": "sensor.open_meteo_bad_watts",
        "state": "0",
        "attributes": {"watts": "not a dict"},
        "expected_format": None,
        "description": "Open-Meteo sensor with watts not being a dict",
    },
    {
        "entity_id": "sensor.open_meteo_bad_timestamp",
        "state": "0",
        "attributes": {"watts": {"not a timestamp": 100}},
        "expected_format": None,  # Should fail detection due to invalid timestamp
        "description": "Open-Meteo sensor with invalid timestamp",
    },
]
