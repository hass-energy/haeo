"""Discriminated union types for schema input values."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from numbers import Real
import types
from typing import Any, Final, Literal, TypedDict, TypeAliasType, TypeGuard, Union, get_args, get_origin

VALUE_TYPE_ENTITY: Final = "entity"
VALUE_TYPE_CONSTANT: Final = "constant"
VALUE_TYPE_NONE: Final = "none"


class EntityValue(TypedDict):
    """Schema value representing entity-based inputs."""

    type: Literal["entity"]
    value: list[str]


class ConstantValue(TypedDict):
    """Schema value representing constant inputs."""

    type: Literal["constant"]
    value: float | bool


class NoneValue(TypedDict):
    """Schema value representing a disabled input."""

    type: Literal["none"]


type SchemaValue = EntityValue | ConstantValue | NoneValue
type EntityOrConstantValue = EntityValue | ConstantValue
type OptionalEntityOrConstantValue = EntityValue | ConstantValue | NoneValue
type SchemaValueKind = Literal["entity", "constant", "none"]


def normalize_entity_ids(value: Sequence[str] | str) -> list[str]:
    """Normalize entity IDs into a list of strings."""
    if isinstance(value, str):
        return [value]
    return list(value)


def as_entity_value(value: Sequence[str] | str) -> EntityValue:
    """Create an entity schema value from entity IDs."""
    return {"type": VALUE_TYPE_ENTITY, "value": normalize_entity_ids(value)}


def as_constant_value(value: float | bool) -> ConstantValue:
    """Create a constant schema value from a scalar."""
    return {"type": VALUE_TYPE_CONSTANT, "value": value}


def as_none_value() -> NoneValue:
    """Create a disabled schema value."""
    return {"type": VALUE_TYPE_NONE}


def is_entity_value(value: Any) -> TypeGuard[EntityValue]:
    """Return True if value is an entity schema value."""
    if not isinstance(value, Mapping):
        return False
    if value.get("type") != VALUE_TYPE_ENTITY:
        return False
    entity_list = value.get("value")
    return isinstance(entity_list, list) and all(isinstance(item, str) for item in entity_list)


def is_constant_value(value: Any) -> TypeGuard[ConstantValue]:
    """Return True if value is a constant schema value."""
    if not isinstance(value, Mapping):
        return False
    if value.get("type") != VALUE_TYPE_CONSTANT:
        return False
    constant = value.get("value")
    if isinstance(constant, bool):
        return True
    return isinstance(constant, Real)


def is_none_value(value: Any) -> TypeGuard[NoneValue]:
    """Return True if value is a disabled schema value."""
    if not isinstance(value, Mapping):
        return False
    return value.get("type") == VALUE_TYPE_NONE


def is_schema_value(value: Any) -> TypeGuard[SchemaValue]:
    """Return True if value is a known schema value variant."""
    return is_entity_value(value) or is_constant_value(value) or is_none_value(value)


def extract_entity_ids(value: SchemaValue) -> list[str] | None:
    """Extract entity IDs from a schema value."""
    if value["type"] == VALUE_TYPE_ENTITY:
        return value["value"]
    return None


def extract_constant(value: SchemaValue) -> float | bool | None:
    """Extract constant scalar from a schema value."""
    if value["type"] == VALUE_TYPE_CONSTANT:
        return value["value"]
    return None


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
        mapping = {
            EntityValue: VALUE_TYPE_ENTITY,
            ConstantValue: VALUE_TYPE_CONSTANT,
            NoneValue: VALUE_TYPE_NONE,
        }
        return frozenset({mapping[value_type]})

    return frozenset()


__all__ = [
    "ConstantValue",
    "EntityValue",
    "EntityOrConstantValue",
    "NoneValue",
    "OptionalEntityOrConstantValue",
    "SchemaValue",
    "SchemaValueKind",
    "VALUE_TYPE_CONSTANT",
    "VALUE_TYPE_ENTITY",
    "VALUE_TYPE_NONE",
    "as_constant_value",
    "as_entity_value",
    "as_none_value",
    "extract_constant",
    "extract_entity_ids",
    "get_schema_value_kinds",
    "is_constant_value",
    "is_entity_value",
    "is_none_value",
    "is_schema_value",
    "normalize_entity_ids",
]
