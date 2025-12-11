"""Test data aggregator for element configurations."""

from collections.abc import Mapping, Sequence
from typing import Any

from custom_components.haeo.elements import ElementType

from . import battery as battery_data
from . import connection as connection_data
from . import grid as grid_data
from . import load as load_data
from . import node as node_data
from . import photovoltaics as pv_data
from .types import ElementValidCase

INVALID_CONFIGS_BY_TYPE: Mapping[str, Sequence[dict[str, Any]]] = {
    "battery": getattr(battery_data, "INVALID_SCHEMA", []),
    "grid": getattr(grid_data, "INVALID_SCHEMA", []),
    "connection": getattr(connection_data, "INVALID_SCHEMA", []),
    "photovoltaics": getattr(pv_data, "INVALID_SCHEMA", []),
    "load": getattr(load_data, "INVALID_SCHEMA", []),
    "node": getattr(node_data, "INVALID_SCHEMA", []),
}

VALID_CONFIGS_BY_TYPE: Mapping[ElementType, Sequence[ElementValidCase[Any, Any]]] = {
    "battery": battery_data.VALID,
    "grid": grid_data.VALID,
    "connection": connection_data.VALID,
    "photovoltaics": pv_data.VALID,
    "load": load_data.VALID,
    "node": node_data.VALID,
}

__all__ = [
    "ElementValidCase",
    "INVALID_CONFIGS_BY_TYPE",
    "VALID_CONFIGS_BY_TYPE",
]
