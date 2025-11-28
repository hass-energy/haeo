"""Test data aggregator for forecast sensor configurations.

This module aggregates test data from all parser types and organizes them
by parser type for easy access in parameterized tests.
"""

from typing import Any

from . import aemo, amberelectric, haeo, open_meteo, solcast

# Aggregate all valid sensor configs by parser type
VALID_SENSORS_BY_PARSER: dict[str, list[dict[str, Any]]] = {
    "amberelectric": amberelectric.VALID,
    "aemo_nem": aemo.VALID,
    "haeo": haeo.VALID,
    "solcast_solar": solcast.VALID,
    "open_meteo_solar_forecast": open_meteo.VALID,
}

# Aggregate all invalid sensor configs by parser type
INVALID_SENSORS_BY_PARSER: dict[str, list[dict[str, Any]]] = {
    "amberelectric": amberelectric.INVALID,
    "aemo_nem": aemo.INVALID,
    "haeo": haeo.INVALID,
    "solcast_solar": solcast.INVALID,
    "open_meteo_solar_forecast": open_meteo.INVALID,
}

# Flatten all valid sensors into a single list for easy iteration
ALL_VALID_SENSORS: list[tuple[str, dict[str, Any]]] = [
    (parser_type, sensor) for parser_type, sensors in VALID_SENSORS_BY_PARSER.items() for sensor in sensors
]

# Flatten all invalid sensors
ALL_INVALID_SENSORS: list[tuple[str, dict[str, Any]]] = [
    (parser_type, sensor) for parser_type, sensors in INVALID_SENSORS_BY_PARSER.items() for sensor in sensors
]
