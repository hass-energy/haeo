"""Test data for HAEO forecast sensors."""

from datetime import UTC, datetime
from typing import Any

VALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.haeo_power_forecast",
        "state": "100.0",
        "attributes": {
            "forecast": [{"time": "2025-10-06T00:00:00+11:00", "value": 100.0}],
            "unit_of_measurement": "W",
            "device_class": "power",
        },
        "expected_format": "haeo",
        "expected_unit": "kW",
        "expected_data": [(1759669200.0, 0.1)],
        "description": "Single HAEO forecast entry with power",
    },
    {
        "entity_id": "sensor.haeo_multi_forecast",
        "state": "50.0",
        "attributes": {
            "forecast": [
                {"time": "2025-10-06T00:00:00+11:00", "value": 50.0},
                {"time": "2025-10-06T00:30:00+11:00", "value": 75.0},
                {"time": "2025-10-06T01:00:00+11:00", "value": 100.0},
            ],
            "unit_of_measurement": "kW",
            "device_class": "power",
        },
        "expected_format": "haeo",
        "expected_unit": "kW",
        "expected_data": [(1759669200.0, 50.0), (1759671000.0, 75.0), (1759672800.0, 100.0)],
        "description": "Multiple HAEO forecast entries",
    },
    {
        "entity_id": "sensor.haeo_datetime_objects",
        "state": "25.0",
        "attributes": {
            "forecast": [
                {"time": datetime(2025, 10, 6, 0, 0, 0, tzinfo=UTC), "value": 25.0},
                {"time": datetime(2025, 10, 6, 0, 30, 0, tzinfo=UTC), "value": 50.0},
            ],
            "unit_of_measurement": "W",
            "device_class": "power",
        },
        "expected_format": "haeo",
        "expected_unit": "kW",
        "expected_data": [(1759708800.0, 0.025), (1759710600.0, 0.05)],
        "description": "HAEO forecast with datetime objects",
    },
    {
        "entity_id": "sensor.haeo_energy_forecast",
        "state": "10.5",
        "attributes": {
            "forecast": [
                {"time": "2025-10-06T00:00:00+11:00", "value": 10.5},
                {"time": "2025-10-06T01:00:00+11:00", "value": 12.0},
            ],
            "unit_of_measurement": "kWh",
            "device_class": "energy",
        },
        "expected_format": "haeo",
        "expected_unit": "kWh",
        "expected_data": [(1759669200.0, 10.5), (1759672800.0, 12.0)],
        "description": "HAEO forecast with energy device class",
    },
    {
        "entity_id": "sensor.haeo_no_device_class",
        "state": "5.0",
        "attributes": {
            "forecast": [{"time": "2025-10-06T00:00:00+11:00", "value": 5.0}],
            "unit_of_measurement": "W",
        },
        "expected_format": "haeo",
        "expected_unit": "kW",
        "expected_data": [(1759669200.0, 0.005)],
        "description": "HAEO forecast without device_class attribute",
    },
    {
        "entity_id": "sensor.haeo_integer_values",
        "state": "100",
        "attributes": {
            "forecast": [
                {"time": "2025-10-06T00:00:00+11:00", "value": 100},
                {"time": "2025-10-06T00:30:00+11:00", "value": 200},
            ],
            "unit_of_measurement": "W",
            "device_class": "power",
        },
        "expected_format": "haeo",
        "expected_unit": "kW",
        "expected_data": [(1759669200.0, 0.1), (1759671000.0, 0.2)],
        "description": "HAEO forecast with integer values (should be converted to float)",
    },
    {
        "entity_id": "sensor.haeo_invalid_device_class",
        "state": "100.0",
        "attributes": {
            "forecast": [{"time": "2025-10-06T00:00:00+11:00", "value": 100.0}],
            "unit_of_measurement": "W",
            "device_class": "invalid_device_class",
        },
        "expected_format": "haeo",
        "expected_unit": "kW",
        "expected_data": [(1759669200.0, 0.1)],
        "description": "HAEO forecast with invalid device_class (should be ignored)",
    },
]

INVALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.haeo_no_forecast",
        "state": "0",
        "attributes": {"unit_of_measurement": "W", "device_class": "power"},
        "expected_format": None,
        "description": "HAEO sensor missing forecast attribute",
    },
    {
        "entity_id": "sensor.haeo_empty_forecast",
        "state": "0",
        "attributes": {"forecast": [], "unit_of_measurement": "W"},
        "expected_format": None,
        "description": "HAEO sensor with empty forecast list",
    },
    {
        "entity_id": "sensor.haeo_forecast_not_list",
        "state": "0",
        "attributes": {"forecast": {"some": "dict"}, "unit_of_measurement": "W"},
        "expected_format": None,
        "description": "HAEO sensor with forecast as dict instead of list",
    },
    {
        "entity_id": "sensor.haeo_bad_timestamp",
        "state": "0",
        "attributes": {
            "forecast": [{"time": "not a timestamp", "value": 100.0}],
            "unit_of_measurement": "W",
        },
        "expected_format": None,
        "description": "HAEO sensor with invalid timestamp",
    },
    {
        "entity_id": "sensor.haeo_non_numeric_value",
        "state": "0",
        "attributes": {
            "forecast": [{"time": "2025-10-06T00:00:00+11:00", "value": "not a number"}],
            "unit_of_measurement": "W",
        },
        "expected_format": None,
        "description": "HAEO sensor with non-numeric forecast value",
    },
    {
        "entity_id": "sensor.haeo_missing_time_field",
        "state": "0",
        "attributes": {"forecast": [{"value": 50.0}], "unit_of_measurement": "W"},
        "expected_format": None,
        "description": "HAEO forecast entry missing time field",
    },
    {
        "entity_id": "sensor.haeo_missing_value_field",
        "state": "0",
        "attributes": {
            "forecast": [{"time": "2025-10-06T00:00:00+11:00"}],
            "unit_of_measurement": "W",
        },
        "expected_format": None,
        "description": "HAEO forecast entry missing value field",
    },
    {
        "entity_id": "sensor.haeo_missing_unit",
        "state": "0",
        "attributes": {"forecast": [{"time": "2025-10-06T00:00:00+11:00", "value": 100.0}]},
        "expected_format": None,
        "description": "HAEO sensor missing unit_of_measurement attribute",
    },
    {
        "entity_id": "sensor.haeo_non_string_unit",
        "state": "0",
        "attributes": {
            "forecast": {"2025-10-06T00:00:00+11:00": 100.0},
            "unit_of_measurement": 123,
        },
        "expected_format": None,
        "description": "HAEO sensor with non-string unit_of_measurement",
    },
    {
        "entity_id": "sensor.haeo_empty_unit",
        "state": "0",
        "attributes": {
            "forecast": {"2025-10-06T00:00:00+11:00": 100.0},
            "unit_of_measurement": "",
        },
        "expected_format": None,
        "description": "HAEO sensor with empty string unit_of_measurement",
    },
]
