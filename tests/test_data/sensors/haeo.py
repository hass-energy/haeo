"""Test data for HAEO forecast sensors."""

from datetime import UTC, datetime
from typing import Any

# Valid HAEO sensor configurations
VALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.haeo_power_forecast",
        "state": "100.0",
        "attributes": {
            "forecast": {
                "2025-10-06T00:00:00+11:00": 100.0,
            },
            "unit_of_measurement": "W",
            "device_class": "power",
        },
        "expected_format": "haeo",
        "expected_count": 1,
        "description": "Single HAEO forecast entry with power",
    },
    {
        "entity_id": "sensor.haeo_multi_forecast",
        "state": "50.0",
        "attributes": {
            "forecast": {
                "2025-10-06T00:00:00+11:00": 50.0,
                "2025-10-06T00:30:00+11:00": 75.0,
                "2025-10-06T01:00:00+11:00": 100.0,
            },
            "unit_of_measurement": "kW",
            "device_class": "power",
        },
        "expected_format": "haeo",
        "expected_count": 3,
        "description": "Multiple HAEO forecast entries",
    },
    {
        "entity_id": "sensor.haeo_datetime_objects",
        "state": "25.0",
        "attributes": {
            "forecast": {
                datetime(2025, 10, 6, 0, 0, 0, tzinfo=UTC): 25.0,
                datetime(2025, 10, 6, 0, 30, 0, tzinfo=UTC): 50.0,
            },
            "unit_of_measurement": "W",
            "device_class": "power",
        },
        "expected_format": "haeo",
        "expected_count": 2,
        "description": "HAEO forecast with datetime objects as keys",
    },
    {
        "entity_id": "sensor.haeo_energy_forecast",
        "state": "10.5",
        "attributes": {
            "forecast": {
                "2025-10-06T00:00:00+11:00": 10.5,
                "2025-10-06T01:00:00+11:00": 12.0,
            },
            "unit_of_measurement": "kWh",
            "device_class": "energy",
        },
        "expected_format": "haeo",
        "expected_count": 2,
        "description": "HAEO forecast with energy device class",
    },
    {
        "entity_id": "sensor.haeo_no_device_class",
        "state": "5.0",
        "attributes": {
            "forecast": {
                "2025-10-06T00:00:00+11:00": 5.0,
            },
            "unit_of_measurement": "W",
        },
        "expected_format": "haeo",
        "expected_count": 1,
        "description": "HAEO forecast without device_class attribute",
    },
    {
        "entity_id": "sensor.haeo_integer_values",
        "state": "100",
        "attributes": {
            "forecast": {
                "2025-10-06T00:00:00+11:00": 100,
                "2025-10-06T00:30:00+11:00": 200,
            },
            "unit_of_measurement": "W",
            "device_class": "power",
        },
        "expected_format": "haeo",
        "expected_count": 2,
        "description": "HAEO forecast with integer values (should be converted to float)",
    },
    {
        "entity_id": "sensor.haeo_invalid_device_class",
        "state": "100.0",
        "attributes": {
            "forecast": {
                "2025-10-06T00:00:00+11:00": 100.0,
            },
            "unit_of_measurement": "W",
            "device_class": "invalid_device_class",
        },
        "expected_format": "haeo",
        "expected_count": 1,
        "description": "HAEO forecast with invalid device_class (should be ignored)",
    },
]

# Invalid HAEO sensor configurations
INVALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.haeo_no_forecast",
        "state": "0",
        "attributes": {
            "unit_of_measurement": "W",
            "device_class": "power",
        },
        "expected_format": None,
        "description": "HAEO sensor missing forecast attribute",
    },
    {
        "entity_id": "sensor.haeo_empty_forecast",
        "state": "0",
        "attributes": {
            "forecast": {},
            "unit_of_measurement": "W",
        },
        "expected_format": None,
        "description": "HAEO sensor with empty forecast mapping",
    },
    {
        "entity_id": "sensor.haeo_forecast_not_mapping",
        "state": "0",
        "attributes": {
            "forecast": [1.0, 2.0, 3.0],
            "unit_of_measurement": "W",
        },
        "expected_format": None,
        "description": "HAEO sensor with forecast as list instead of mapping",
    },
    {
        "entity_id": "sensor.haeo_bad_timestamp",
        "state": "0",
        "attributes": {
            "forecast": {
                "not a timestamp": 100.0,
            },
            "unit_of_measurement": "W",
        },
        "expected_format": None,
        "description": "HAEO sensor with invalid timestamp key",
    },
    {
        "entity_id": "sensor.haeo_non_numeric_value",
        "state": "0",
        "attributes": {
            "forecast": {
                "2025-10-06T00:00:00+11:00": "not a number",
            },
            "unit_of_measurement": "W",
        },
        "expected_format": None,
        "description": "HAEO sensor with non-numeric forecast value",
    },
    {
        "entity_id": "sensor.haeo_mixed_valid_invalid_keys",
        "state": "0",
        "attributes": {
            "forecast": {
                "2025-10-06T00:00:00+11:00": 50.0,
                "corrupt": 100.0,
            },
            "unit_of_measurement": "W",
        },
        "expected_format": None,
        "description": "HAEO forecast with mixed valid and invalid timestamp keys",
    },
    {
        "entity_id": "sensor.haeo_mixed_valid_invalid_values",
        "state": "0",
        "attributes": {
            "forecast": {
                "2025-10-06T00:00:00+11:00": 50.0,
                "2025-10-06T00:30:00+11:00": "invalid",
            },
            "unit_of_measurement": "W",
        },
        "expected_format": None,
        "description": "HAEO forecast with mixed valid and invalid values",
    },
    {
        "entity_id": "sensor.haeo_missing_unit",
        "state": "0",
        "attributes": {
            "forecast": {
                "2025-10-06T00:00:00+11:00": 100.0,
            },
        },
        "expected_format": None,
        "description": "HAEO sensor missing unit_of_measurement attribute",
    },
    {
        "entity_id": "sensor.haeo_non_string_unit",
        "state": "0",
        "attributes": {
            "forecast": {
                "2025-10-06T00:00:00+11:00": 100.0,
            },
            "unit_of_measurement": 123,
        },
        "expected_format": None,
        "description": "HAEO sensor with non-string unit_of_measurement",
    },
    {
        "entity_id": "sensor.haeo_empty_unit",
        "state": "0",
        "attributes": {
            "forecast": {
                "2025-10-06T00:00:00+11:00": 100.0,
            },
            "unit_of_measurement": "",
        },
        "expected_format": None,
        "description": "HAEO sensor with empty string unit_of_measurement",
    },
]
