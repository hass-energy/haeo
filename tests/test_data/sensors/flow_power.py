"""Test data for Flow Power HA forecast sensors."""

from typing import Any

# Timestamps for 2026-01-14 in Australia/Sydney (+1100)
# 12:00:00+1100 = 01:00:00 UTC = 1768352400
# 12:30:00+1100 = 01:30:00 UTC = 1768354200
# 13:00:00+1100 = 02:00:00 UTC = 1768356000
# 17:30:00+1100 = 06:30:00 UTC = 1768372200
# 18:00:00+1100 = 07:00:00 UTC = 1768374000

VALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.flow_power_export_price",
        "state": "0",
        "attributes": {
            "region": "NSW1",
            "unit": "$/kWh",
            "forecast_dict": {
                "2026-01-14 12:00:00+1100": 0,
                "2026-01-14 12:30:00+1100": 0.15,
            },
            "unit_of_measurement": "$/kWh",
            "device_class": "monetary",
            "friendly_name": "Flow Power (NSW1) Export Price",
        },
        "expected_format": "flow_power",
        "expected_unit": "$/kWh",
        # Step function: each period produces (start, price) and (end, price)
        "expected_data": [
            (1768352400.0, 0.0),  # Start of first period (12:00)
            (1768354200.0, 0.0),  # End of first period (12:30) / Start of second
            (1768354200.0, 0.15),  # Start of second period (12:30)
            (1768356000.0, 0.15),  # End of second period (13:00)
        ],
        "description": "Flow Power export price with two periods",
    },
    {
        "entity_id": "sensor.flow_power_import_price",
        "state": "0.35",
        "attributes": {
            "region": "NSW1",
            "unit": "$/kWh",
            "forecast_dict": {
                "2026-01-14 17:30:00+1100": 0.45,
            },
            "price_cents": 35,
            "is_happy_hour": True,
            "happy_hour_rate": 0.45,
            "happy_hour_start": "17:30",
            "happy_hour_end": "19:30",
            "unit_of_measurement": "$/kWh",
            "device_class": "monetary",
            "friendly_name": "Flow Power (NSW1) Import Price",
        },
        "expected_format": "flow_power",
        "expected_unit": "$/kWh",
        # Single entry: no way to determine period length, just emit start point
        "expected_data": [
            (1768372200.0, 0.45),  # Start of period (17:30)
        ],
        "description": "Flow Power import price single period (Happy Hour)",
    },
]

# Invalid Flow Power sensor configurations
INVALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.flow_power_no_forecast",
        "state": "0",
        "attributes": {
            "region": "NSW1",
            "unit_of_measurement": "$/kWh",
        },
        "expected_format": None,
        "description": "Flow Power sensor missing forecast_dict attribute",
    },
    {
        "entity_id": "sensor.flow_power_bad_forecast",
        "state": "0",
        "attributes": {"forecast_dict": "not a dict"},
        "expected_format": None,
        "description": "Flow Power sensor with forecast_dict not being a mapping",
    },
    {
        "entity_id": "sensor.flow_power_empty_forecast",
        "state": "0",
        "attributes": {"forecast_dict": {}},
        "expected_format": None,
        "description": "Flow Power sensor with empty forecast_dict",
    },
    {
        "entity_id": "sensor.flow_power_bad_timestamp",
        "state": "0",
        "attributes": {"forecast_dict": {"not a timestamp": 0.1}},
        "expected_format": None,
        "description": "Flow Power sensor with invalid timestamp key",
    },
    {
        "entity_id": "sensor.flow_power_bad_value",
        "state": "0",
        "attributes": {"forecast_dict": {"2026-01-14 12:00:00+1100": "not a number"}},
        "expected_format": None,
        "description": "Flow Power sensor with non-numeric price value",
    },
]
