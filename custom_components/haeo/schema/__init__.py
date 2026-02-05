"""Schema utilities for HAEO type configurations."""

from .connection_target import (
    ConnectionTarget,
    ConnectionTargetValue,
    as_connection_target,
    extract_connection_target,
    get_connection_target_name,
    is_connection_target,
    normalize_connection_target,
)
from .constant_value import ConstantValue, as_constant_value, extract_constant, is_constant_value
from .entity_value import EntityValue, as_entity_value, extract_entity_ids, is_entity_value
from .none_value import NoneValue, as_none_value, is_none_value
from .types import EntityOrConstantValue, OptionalEntityOrConstantValue, SchemaValue, SchemaValueKind
from .util import UnitSpec, matches_unit_spec
from .value_kinds import VALUE_TYPE_CONNECTION_TARGET, VALUE_TYPE_CONSTANT, VALUE_TYPE_ENTITY, VALUE_TYPE_NONE
from .value_utils import get_schema_value_kinds, is_schema_value

__all__ = [
    "VALUE_TYPE_CONNECTION_TARGET",
    "VALUE_TYPE_CONSTANT",
    "VALUE_TYPE_ENTITY",
    "VALUE_TYPE_NONE",
    "ConnectionTarget",
    "ConnectionTargetValue",
    "ConstantValue",
    "EntityOrConstantValue",
    "EntityValue",
    "NoneValue",
    "OptionalEntityOrConstantValue",
    "SchemaValue",
    "SchemaValueKind",
    "UnitSpec",
    "as_connection_target",
    "as_constant_value",
    "as_entity_value",
    "as_none_value",
    "extract_connection_target",
    "extract_constant",
    "extract_entity_ids",
    "get_connection_target_name",
    "get_schema_value_kinds",
    "is_connection_target",
    "is_constant_value",
    "is_entity_value",
    "is_none_value",
    "is_schema_value",
    "matches_unit_spec",
    "normalize_connection_target",
]
