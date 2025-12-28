"""Tests for schema utilities covering loader dispatch."""

from typing import Annotated, TypedDict

from custom_components.haeo.data.loader import ConstantLoader
from custom_components.haeo.schema import compose_field, get_default, get_loader_instance
from custom_components.haeo.schema.fields import Constant, Default, PositiveKW


def test_compose_field_extracts_all_metadata() -> None:
    """compose_field() extracts Validator, LoaderMeta, and Default from Annotated."""
    field_type = Annotated[float, PositiveKW(), Constant(float), Default(value=5.0)]
    spec = compose_field(field_type)

    assert isinstance(spec.validator, PositiveKW)
    assert isinstance(spec.loader, Constant)
    assert spec.default is not None
    assert spec.default.value == 5.0


def test_compose_field_handles_missing_metadata() -> None:
    """compose_field() returns None for missing metadata components."""
    # Type with only validator
    field_type = Annotated[float, PositiveKW()]
    spec = compose_field(field_type)

    assert isinstance(spec.validator, PositiveKW)
    assert spec.loader is None
    assert spec.default is None


def test_get_loader_instance_returns_correct_loader_for_constant() -> None:
    """get_loader_instance returns ConstantLoader for Constant fields."""

    class ConfigData(TypedDict):
        power: Annotated[float, PositiveKW(), Constant(float)]

    loader = get_loader_instance("power", ConfigData)
    assert isinstance(loader, ConstantLoader)


def test_get_loader_instance_returns_default_for_missing_field() -> None:
    """get_loader_instance returns default loader for missing fields."""

    class ConfigData(TypedDict):
        pass

    loader = get_loader_instance("nonexistent", ConfigData)
    assert isinstance(loader, ConstantLoader)


def test_get_default_returns_default_value_from_annotation() -> None:
    """get_default extracts default value from Annotated type."""

    class ConfigData(TypedDict):
        power: Annotated[float, PositiveKW(), Constant(float), Default(value=5.0)]

    result = get_default("power", ConfigData, 0.0)
    assert result == 5.0


def test_get_default_returns_fallback_for_missing_field() -> None:
    """get_default returns fallback when field doesn't exist."""

    class ConfigData(TypedDict):
        power: Annotated[float, PositiveKW(), Constant(float)]

    # Field "nonexistent" doesn't exist in ConfigData
    result = get_default("nonexistent", ConfigData, 42.0)
    assert result == 42.0


def test_get_default_returns_fallback_when_no_default_annotation() -> None:
    """get_default returns fallback when field has no Default annotation."""

    class ConfigData(TypedDict):
        power: Annotated[float, PositiveKW(), Constant(float)]

    # Field exists but has no Default annotation
    result = get_default("power", ConfigData, 99.0)
    assert result == 99.0
