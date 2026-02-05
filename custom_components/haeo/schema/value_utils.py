"""Shared helpers for discriminated schema values."""

from __future__ import annotations

import types
from typing import Any, TypeAliasType, TypeGuard, Union, get_args, get_origin

from .constant_value import ConstantValue, is_constant_value
from .entity_value import EntityValue, is_entity_value
from .none_value import NoneValue, is_none_value
from .types import SchemaValue
from .value_kinds import VALUE_TYPE_CONSTANT, VALUE_TYPE_ENTITY, VALUE_TYPE_NONE, SchemaValueKind


def is_schema_value(value: Any) -> TypeGuard[SchemaValue]:
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
    "get_schema_value_kinds",
    "is_schema_value",
]
