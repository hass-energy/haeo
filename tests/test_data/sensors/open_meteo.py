"""Test data for Open-Meteo Solar forecast sensors."""

from typing import Any

# Valid Open-Meteo sensor configurations
# Open-Meteo returns power in W, converted to kW via device_class=POWER
# Timestamps: 2025-10-06T06:45:00+11:00 = 2025-10-05T19:45:00Z = 1759693500
#             2025-10-06T07:00:00+11:00 = 2025-10-05T20:00:00Z = 1759694400
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
        "expected_unit": "kW",
        # 175 W = 0.175 kW, 200 W = 0.2 kW
        "expected_data": [
            (1759693500.0, 0.175),
            (1759694400.0, 0.2),
        ],
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
        "expected_unit": "kW",
        # 175 W = 0.175 kW, 200 W = 0.2 kW
        "expected_data": [
            (1759693500.0, 0.175),
            (1759694400.0, 0.2),
        ],
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
    {
        "entity_id": "sensor.open_meteo_mixed_valid_invalid",
        "state": "0",
        "attributes": {
            "watts": {
                "2025-10-06T06:45:00+11:00": 175,
                "bad": 42,
            }
        },
        "expected_format": None,
        "expected_count": 0,
        "description": "Open-Meteo forecast containing both valid and invalid rows",
    },
    {
        "entity_id": "sensor.open_meteo_non_string_key",
        "state": "0",
        "attributes": {
            "watts": {
                "2025-10-06T06:45:00+11:00": 175,
                123: 50,
            }
        },
        "expected_format": None,
        "expected_count": 0,
        "description": "Open-Meteo forecast containing a non-string timestamp key",
    },
]
