"""Tests for schema value utilities."""

from custom_components.haeo.core.schema import (
    VALUE_TYPE_CALENDAR,
    VALUE_TYPE_CONSTANT,
    VALUE_TYPE_ENTITY,
    VALUE_TYPE_NONE,
    CalendarValue,
    ConstantValue,
    EntityValue,
    NoneValue,
    as_calendar_value,
    as_constant_value,
    as_entity_value,
    as_none_value,
    get_schema_value_kinds,
    is_schema_value,
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
    assert get_schema_value_kinds(CalendarValue) == {VALUE_TYPE_CALENDAR}


def test_get_schema_value_kinds_returns_empty_for_unknown() -> None:
    """get_schema_value_kinds returns empty set for unknown types."""
    assert get_schema_value_kinds(str) == frozenset()


def test_is_schema_value_recognizes_all_variants() -> None:
    """is_schema_value accepts every member of the SchemaValue union."""
    assert is_schema_value(as_entity_value(["sensor.power"]))
    assert is_schema_value(as_constant_value(1.5))
    assert is_schema_value(as_none_value())
    assert is_schema_value(as_calendar_value("calendar.trips"))


def test_is_schema_value_rejects_non_schema_values() -> None:
    """is_schema_value rejects plain values and unknown mappings."""
    assert not is_schema_value(None)
    assert not is_schema_value(1.5)
    assert not is_schema_value("sensor.power")
    assert not is_schema_value({"type": "unknown", "value": 1})
