"""Tests for schema value utilities."""

from custom_components.haeo.schema import (
    VALUE_TYPE_CONSTANT,
    VALUE_TYPE_ENTITY,
    VALUE_TYPE_NONE,
    ConstantValue,
    EntityValue,
    NoneValue,
    get_schema_value_kinds,
)

type ValueAlias = EntityValue | NoneValue


def test_get_schema_value_kinds_handles_union_and_alias() -> None:
    """get_schema_value_kinds returns kinds for unions and aliases."""
    kinds = get_schema_value_kinds(ValueAlias)
    assert kinds == {VALUE_TYPE_ENTITY, VALUE_TYPE_NONE}


def test_get_schema_value_kinds_handles_direct_types() -> None:
    """get_schema_value_kinds returns correct kind for direct types."""
    assert get_schema_value_kinds(EntityValue) == {VALUE_TYPE_ENTITY}
    assert get_schema_value_kinds(ConstantValue) == {VALUE_TYPE_CONSTANT}
    assert get_schema_value_kinds(NoneValue) == {VALUE_TYPE_NONE}


def test_get_schema_value_kinds_returns_empty_for_unknown() -> None:
    """get_schema_value_kinds returns empty set for unknown types."""
    assert get_schema_value_kinds(str) == frozenset()
