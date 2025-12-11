"""Test data aggregator for element configurations."""

from typing import Any, cast

from custom_components.haeo.elements import ElementConfigData, ElementConfigSchema
from custom_components.haeo.elements import battery as battery_mod
from custom_components.haeo.elements import connection as connection_mod
from custom_components.haeo.elements import grid as grid_mod
from custom_components.haeo.elements import load as load_mod
from custom_components.haeo.elements import node as node_mod
from custom_components.haeo.elements import photovoltaics as pv_mod

from . import battery as battery_data
from . import connection as connection_data
from . import grid as grid_data
from . import load as load_data
from . import node as node_data
from . import photovoltaics as pv_data
from .types import ElementValidCase

ADAPTER_HELPERS = {
    "battery": battery_mod,
    "connection": connection_mod,
    "grid": grid_mod,
    "load": load_mod,
    "photovoltaics": pv_mod,
    "node": node_mod,
}

INVALID_CONFIGS_BY_TYPE: dict[str, list[dict[str, Any]]] = {
    "battery": getattr(battery_data, "INVALID_SCHEMA", []),
    "grid": getattr(grid_data, "INVALID_SCHEMA", []),
    "connection": getattr(connection_data, "INVALID_SCHEMA", []),
    "photovoltaics": getattr(pv_data, "INVALID_SCHEMA", []),
    "load": getattr(load_data, "INVALID_SCHEMA", []),
    "node": getattr(node_data, "INVALID_SCHEMA", []),
}

VALID_CONFIGS_BY_TYPE: dict[str, list[ElementValidCase[ElementConfigSchema, ElementConfigData]]] = {
    "battery": cast("list[ElementValidCase[ElementConfigSchema, ElementConfigData]]", battery_data.VALID),
    "grid": cast("list[ElementValidCase[ElementConfigSchema, ElementConfigData]]", grid_data.VALID),
    "connection": cast("list[ElementValidCase[ElementConfigSchema, ElementConfigData]]", connection_data.VALID),
    "photovoltaics": cast(
        "list[ElementValidCase[ElementConfigSchema, ElementConfigData]]",
        pv_data.VALID,
    ),
    "load": cast("list[ElementValidCase[ElementConfigSchema, ElementConfigData]]", load_data.VALID),
    "node": cast("list[ElementValidCase[ElementConfigSchema, ElementConfigData]]", node_data.VALID),
}

ALL_VALID: tuple[ElementValidCase[ElementConfigSchema, ElementConfigData], ...] = tuple(
    case
    for module in (battery_data, connection_data, grid_data, load_data, node_data, pv_data)
    for case in getattr(module, "VALID", [])
)

__all__ = [
    "ADAPTER_HELPERS",
    "ALL_VALID",
    "INVALID_CONFIGS_BY_TYPE",
    "VALID_CONFIGS_BY_TYPE",
    "ElementValidCase",
]
