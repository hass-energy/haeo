"""Test data aggregator for element configurations.

This module aggregates test data from all element types and organizes them
by element_type for easy access in parameterized tests.
"""

from typing import Any

from . import battery, connection, constant_load, forecast_load, grid, node, photovoltaics

# Aggregate all valid configs by element type
VALID_CONFIGS_BY_TYPE: dict[str, list[dict[str, Any]]] = {
    "battery": battery.VALID,
    "grid": grid.VALID,
    "connection": connection.VALID,
    "photovoltaics": photovoltaics.VALID,
    "constant_load": constant_load.VALID,
    "forecast_load": forecast_load.VALID,
    "node": node.VALID,
}

# Aggregate all invalid configs by element type
INVALID_CONFIGS_BY_TYPE: dict[str, list[dict[str, Any]]] = {
    "battery": battery.INVALID,
    "grid": grid.INVALID,
    "connection": connection.INVALID,
    "photovoltaics": photovoltaics.INVALID,
    "constant_load": constant_load.INVALID,
    "forecast_load": forecast_load.INVALID,
    "node": node.INVALID,
}
