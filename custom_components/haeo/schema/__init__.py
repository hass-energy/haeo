"""Schema utilities for HAEO type configurations."""

from __future__ import annotations

import types
from typing import Any, Final, TypeAliasType, Union, get_args, get_origin

from .connection_target import (
    ConnectionTarget,
    ConnectionTargetValue,
    as_connection_target,
    extract_connection_target,
    get_connection_target_name,
    is_connection_target,
    normalize_connection_target,
)
from .constant_value import ConstantValue, as_constant_value, is_constant_value
from .entity_value import EntityValue, as_entity_value, is_entity_value
from .none_value import NoneValue, as_none_value, is_none_value
from .types import EntityOrConstantValue, OptionalEntityOrConstantValue, SchemaValue, SchemaValueKind
from .util import UnitSpec, matches_unit_spec

VALUE_TYPE_ENTITY: Final = "entity"
VALUE_TYPE_CONSTANT: Final = "constant"
VALUE_TYPE_NONE: Final = "none"
VALUE_TYPE_CONNECTION_TARGET: Final = "connection_target"


def is_schema_value(value: Any) -> bool:
    """Return True if value is a known schema value variant."""
    return is_entity_value(value) or is_constant_value(value) or is_none_value(value)


def _unwrap_alias_type(value_type: Any) -> Any:
    if isinstance(value_type, TypeAliasType):
        return value_type.__value__
    return value_type


def get_schema_value_kinds(value_type: Any) -> frozenset[SchemaValueKind]:
    """Return the schema value kinds contained in a type annotation."""
    value_type = _unwrap_alias_type(value_type)
    origin = get_origin(value_type)

    if origin in (types.UnionType, Union):
        kinds: set[SchemaValueKind] = set()
        for arg in get_args(value_type):
            kinds.update(get_schema_value_kinds(arg))
        return frozenset(kinds)

    if value_type in (EntityValue, ConstantValue, NoneValue):
        mapping: dict[type, SchemaValueKind] = {
            EntityValue: VALUE_TYPE_ENTITY,
            ConstantValue: VALUE_TYPE_CONSTANT,
            NoneValue: VALUE_TYPE_NONE,
        }
        return frozenset({mapping[value_type]})

    return frozenset()

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
