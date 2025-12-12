"""Test data aggregator for element configurations."""

from collections.abc import Mapping, Sequence

from custom_components.haeo.elements import ELEMENT_TYPE_BATTERY, ELEMENT_TYPE_CONNECTION, ELEMENT_TYPE_GRID, ELEMENT_TYPE_LOAD, ELEMENT_TYPE_NODE, ElementConfigData, ElementConfigSchema, ElementType, ELEMENT_TYPE_PHOTOVOLTAICS

from . import battery as battery_data
from . import connection as connection_data
from . import grid as grid_data
from . import load as load_data
from . import node as node_data
from . import photovoltaics as pv_data
from .types import ElementValidCase, InvalidModelCase, InvalidSchemaCase

INVALID_SCHEMAS_BY_TYPE: Mapping[ElementType, Sequence[InvalidSchemaCase[ElementConfigSchema]]] = {
    ELEMENT_TYPE_BATTERY: battery_data.INVALID_SCHEMA,
    ELEMENT_TYPE_GRID: grid_data.INVALID_SCHEMA,
    ELEMENT_TYPE_CONNECTION: connection_data.INVALID_SCHEMA,
    ELEMENT_TYPE_PHOTOVOLTAICS: pv_data.INVALID_SCHEMA,
    ELEMENT_TYPE_LOAD: load_data.INVALID_SCHEMA,
    ELEMENT_TYPE_NODE: node_data.INVALID_SCHEMA,
}

VALID_CONFIGS_BY_TYPE: Mapping[ElementType, Sequence[ElementValidCase[ElementConfigSchema, ElementConfigData]]] = {
    ELEMENT_TYPE_BATTERY: battery_data.VALID,
    ELEMENT_TYPE_GRID: grid_data.VALID,
    ELEMENT_TYPE_CONNECTION: connection_data.VALID,
    ELEMENT_TYPE_PHOTOVOLTAICS: pv_data.VALID,
    ELEMENT_TYPE_LOAD: load_data.VALID,
    ELEMENT_TYPE_NODE: node_data.VALID,
}

INVALID_MODEL_PARAMS_BY_TYPE: Mapping[ElementType, Sequence[InvalidModelCase[ElementConfigData]]] = {
    ELEMENT_TYPE_BATTERY: battery_data.INVALID_MODEL_PARAMS,
    ELEMENT_TYPE_GRID: grid_data.INVALID_MODEL_PARAMS,
    ELEMENT_TYPE_CONNECTION: connection_data.INVALID_MODEL_PARAMS,
    ELEMENT_TYPE_PHOTOVOLTAICS: pv_data.INVALID_MODEL_PARAMS,
    ELEMENT_TYPE_LOAD: load_data.INVALID_MODEL_PARAMS,
    ELEMENT_TYPE_NODE: node_data.INVALID_MODEL_PARAMS,
}

__all__ = [
    "ElementValidCase",
    "INVALID_SCHEMAS_BY_TYPE",
    "INVALID_MODEL_PARAMS_BY_TYPE",
    "VALID_CONFIGS_BY_TYPE",
]
