"""Test data for EMHASS energy management forecast sensors.

EMHASS uses a unique format where:
- The attribute key varies by sensor type (forecasts, deferrables_schedule, etc.)
- Each entry has a "date" timestamp and a value key matching the entity name
- Values are stored as strings that parse to floats
"""

from typing import Any

# Timestamps for testing (2025-10-06 in AEST +11:00)
# 2025-10-06T00:00:00+11:00 = 1759669200
# 2025-10-06T00:30:00+11:00 = 1759671000
# 2025-10-06T01:00:00+11:00 = 1759672800

VALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.p_load_forecast",
        "state": "1500.0",
        "attributes": {
            "device_class": "power",
            "unit_of_measurement": "W",
            "friendly_name": "Load Forecast",
            "forecasts": [
                {"date": "2025-10-06T00:00:00+11:00", "p_load_forecast": "1500.0"},
                {"date": "2025-10-06T00:30:00+11:00", "p_load_forecast": "1600.0"},
            ],
        },
        "expected_format": "emhass",
        "expected_unit": "kW",  # Converted from W to base unit kW
        "expected_data": [(1759669200.0, 1.5), (1759671000.0, 1.6)],
        "description": "EMHASS load forecast with forecasts attribute",
    },
    {
        "entity_id": "sensor.p_deferrable0",
        "state": "500.0",
        "attributes": {
            "device_class": "power",
            "unit_of_measurement": "W",
            "friendly_name": "Deferrable Load 0",
            "deferrables_schedule": [
                {"date": "2025-10-06T00:00:00+11:00", "p_deferrable0": "0.0"},
                {"date": "2025-10-06T00:30:00+11:00", "p_deferrable0": "500.0"},
                {"date": "2025-10-06T01:00:00+11:00", "p_deferrable0": "500.0"},
            ],
        },
        "expected_format": "emhass",
        "expected_unit": "kW",
        "expected_data": [(1759669200.0, 0.0), (1759671000.0, 0.5), (1759672800.0, 0.5)],
        "description": "EMHASS deferrable load with deferrables_schedule attribute",
    },
    {
        "entity_id": "sensor.p_pv_forecast",
        "state": "2500",
        "attributes": {
            "device_class": "power",
            "unit_of_measurement": "W",
            "friendly_name": "PV Forecast",
            "forecasts": [
                {"date": "2025-10-06T00:00:00+11:00", "p_pv_forecast": 0},
                {"date": "2025-10-06T00:30:00+11:00", "p_pv_forecast": 2500},
            ],
        },
        "expected_format": "emhass",
        "expected_unit": "kW",
        "expected_data": [(1759669200.0, 0.0), (1759671000.0, 2.5)],
        "description": "EMHASS forecast with numeric values (not strings)",
    },
    {
        "entity_id": "sensor.p_batt_forecast",
        "state": "-1000.0",
        "attributes": {
            "device_class": "power",
            "unit_of_measurement": "W",
            "friendly_name": "Battery Power Forecast",
            "battery_scheduled_power": [
                {"date": "2025-10-06T00:00:00+11:00", "p_batt_forecast": "-1000.0"},
                {"date": "2025-10-06T00:30:00+11:00", "p_batt_forecast": "500.0"},
            ],
        },
        "expected_format": "emhass",
        "expected_unit": "kW",
        "expected_data": [(1759669200.0, -1.0), (1759671000.0, 0.5)],
        "description": "EMHASS battery power with battery_scheduled_power attribute",
    },
    {
        "entity_id": "sensor.soc_batt_forecast",
        "state": "50.0",
        "attributes": {
            "device_class": "battery",
            "unit_of_measurement": "%",
            "friendly_name": "Battery SOC Forecast",
            "battery_scheduled_soc": [
                {"date": "2025-10-06T00:00:00+11:00", "soc_batt_forecast": "50.0"},
                {"date": "2025-10-06T00:30:00+11:00", "soc_batt_forecast": "60.0"},
            ],
        },
        "expected_format": "emhass",
        "expected_unit": "%",  # Battery percentage stays as-is
        "expected_data": [(1759669200.0, 50.0), (1759671000.0, 60.0)],
        "description": "EMHASS battery SOC with battery_scheduled_soc attribute",
    },
    {
        "entity_id": "sensor.unit_load_cost",
        "state": "0.25",
        "attributes": {
            "device_class": "monetary",
            "unit_of_measurement": "AUD/kWh",
            "friendly_name": "Unit Load Cost",
            "unit_load_cost_forecasts": [
                {"date": "2025-10-06T00:00:00+11:00", "unit_load_cost": "0.2500"},
                {"date": "2025-10-06T00:30:00+11:00", "unit_load_cost": "0.3000"},
            ],
        },
        "expected_format": "emhass",
        "expected_unit": "AUD/kWh",
        "expected_data": [(1759669200.0, 0.25), (1759671000.0, 0.30)],
        "description": "EMHASS unit cost forecast with unit_load_cost_forecasts attribute",
    },
    {
        "entity_id": "sensor.mlforecaster_load",
        "state": "1200.0",
        "attributes": {
            "device_class": "power",
            "unit_of_measurement": "W",
            "friendly_name": "ML Forecaster Load",
            "scheduled_forecast": [
                {"date": "2025-10-06T00:00:00+11:00", "mlforecaster_load": "1200.0"},
                {"date": "2025-10-06T00:30:00+11:00", "mlforecaster_load": "1100.0"},
            ],
        },
        "expected_format": "emhass",
        "expected_unit": "kW",
        "expected_data": [(1759669200.0, 1.2), (1759671000.0, 1.1)],
        "description": "EMHASS ML forecaster with scheduled_forecast attribute",
    },
    {
        "entity_id": "sensor.predicted_temp",
        "state": "22.5",
        "attributes": {
            "device_class": "temperature",
            "unit_of_measurement": "°C",
            "friendly_name": "Predicted Temperature",
            "predicted_temperatures": [
                {"date": "2025-10-06T00:00:00+11:00", "predicted_temp": "22.5"},
                {"date": "2025-10-06T00:30:00+11:00", "predicted_temp": "23.0"},
            ],
        },
        "expected_format": "emhass",
        "expected_unit": "°C",
        "expected_data": [(1759669200.0, 22.5), (1759671000.0, 23.0)],
        "description": "EMHASS temperature forecast with predicted_temperatures attribute",
    },
]

INVALID: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.p_load_forecast",
        "state": "1500.0",
        "attributes": {
            "device_class": "power",
            "unit_of_measurement": "W",
            # Missing forecasts attribute
        },
        "expected_format": None,
        "description": "EMHASS sensor missing forecast attribute",
    },
    {
        "entity_id": "sensor.p_load_forecast",
        "state": "1500.0",
        "attributes": {
            "device_class": "power",
            "unit_of_measurement": "W",
            "forecasts": [],  # Empty list
        },
        "expected_format": None,
        "description": "EMHASS sensor with empty forecasts list",
    },
    {
        "entity_id": "sensor.p_load_forecast",
        "state": "1500.0",
        "attributes": {
            "device_class": "power",
            "unit_of_measurement": "W",
            "forecasts": "not a list",
        },
        "expected_format": None,
        "description": "EMHASS sensor with forecasts not being a list",
    },
    {
        "entity_id": "sensor.p_load_forecast",
        "state": "1500.0",
        "attributes": {
            "device_class": "power",
            "unit_of_measurement": "W",
            "forecasts": [
                {"date": "2025-10-06T00:00:00+11:00", "wrong_key": "1500.0"},
            ],
        },
        "expected_format": None,
        "description": "EMHASS sensor with wrong value key (doesn't match entity name)",
    },
    {
        "entity_id": "sensor.p_load_forecast",
        "state": "1500.0",
        "attributes": {
            "device_class": "power",
            "unit_of_measurement": "W",
            "forecasts": [
                {"date": "not a timestamp", "p_load_forecast": "1500.0"},
            ],
        },
        "expected_format": None,
        "description": "EMHASS sensor with invalid timestamp",
    },
    {
        "entity_id": "sensor.p_load_forecast",
        "state": "1500.0",
        "attributes": {
            "device_class": "power",
            "unit_of_measurement": "W",
            "forecasts": [
                {"date": "2025-10-06T00:00:00+11:00", "p_load_forecast": "not_a_number"},
            ],
        },
        "expected_format": None,
        "description": "EMHASS sensor with non-numeric value",
    },
    {
        "entity_id": "sensor.p_load_forecast",
        "state": "1500.0",
        "attributes": {
            "device_class": "power",
            "unit_of_measurement": "W",
            "forecasts": [
                {"p_load_forecast": "1500.0"},  # Missing date key
            ],
        },
        "expected_format": None,
        "description": "EMHASS sensor with missing date key",
    },
    {
        "entity_id": "sensor.p_load_forecast",
        "state": "1500.0",
        "attributes": {
            "device_class": "power",
            "unit_of_measurement": "W",
            "forecasts": [
                {"date": "2025-10-06T00:00:00+11:00", "p_load_forecast": "1500.0"},
                {"date": "2025-10-06T00:30:00+11:00", "p_load_forecast": "invalid"},
            ],
        },
        "expected_format": None,
        "description": "EMHASS sensor with mixed valid and invalid entries",
    },
    {
        "entity_id": "sensor.p_load_forecast",
        "state": "1500.0",
        "attributes": {
            "device_class": "power",
            "unit_of_measurement": "W",
            "forecasts": [
                {"date": "2025-10-06T00:00:00+11:00", "p_load_forecast": ["not", "a", "number"]},
            ],
        },
        "expected_format": None,
        "description": "EMHASS sensor with value that is a list instead of numeric",
    },
]
