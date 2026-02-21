"""Tests for elements schema helper utilities."""

from typing import Any, Literal, NotRequired, Required, TypeAliasType, TypedDict

import pytest

from custom_components.haeo import elements as elements_module
from custom_components.haeo.elements import battery, get_input_field_schema_info


class _DummySection(TypedDict):
    field: str


DummySectionAlias = TypeAliasType("DummySectionAlias", _DummySection)


class _DummySchema(TypedDict):
    element_type: Literal["battery"]
    dummy: DummySectionAlias


def test_get_input_field_schema_info_marks_optional_fields() -> None:
    """get_input_field_schema_info marks optional fields and sections."""
    input_fields = battery.adapter.inputs(None)
    schema_info = get_input_field_schema_info(battery.ELEMENT_TYPE, input_fields)

    assert schema_info[battery.SECTION_STORAGE][battery.CONF_CAPACITY].is_optional is False
    assert schema_info[battery.SECTION_LIMITS][battery.CONF_MIN_CHARGE_PERCENTAGE].is_optional is True
    assert schema_info[battery.SECTION_PRICING][battery.CONF_SALVAGE_VALUE].is_optional is False


def test_get_input_field_schema_info_missing_section() -> None:
    """get_input_field_schema_info raises when section is missing."""
    input_fields = dict(battery.adapter.inputs(None))
    input_fields["missing_section"] = {}

    with pytest.raises(RuntimeError, match="Section 'missing_section' not found"):
        get_input_field_schema_info(battery.ELEMENT_TYPE, input_fields)


def test_get_input_field_schema_info_section_not_typed_dict() -> None:
    """get_input_field_schema_info raises when section is not a TypedDict."""
    input_fields = battery.adapter.inputs(None)
    sample_field = input_fields[battery.SECTION_STORAGE][battery.CONF_CAPACITY]

    with pytest.raises(RuntimeError, match="Section 'element_type'.*not a TypedDict"):
        get_input_field_schema_info(
            battery.ELEMENT_TYPE,
            {"element_type": {"field": sample_field}},
        )


def test_get_input_field_schema_info_missing_field() -> None:
    """get_input_field_schema_info raises when a field is missing in schema."""
    input_fields = battery.adapter.inputs(None)
    sample_field = input_fields[battery.SECTION_STORAGE][battery.CONF_CAPACITY]

    with pytest.raises(RuntimeError, match="Field 'storage.missing_field' not found"):
        get_input_field_schema_info(
            battery.ELEMENT_TYPE,
            {battery.SECTION_STORAGE: {"missing_field": sample_field}},
        )


def test_get_input_field_schema_info_type_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_input_field_schema_info unwraps TypeAliasType sections."""
    original_get_type_hints = elements_module.get_type_hints

    def _fake_get_type_hints(schema_cls: type) -> dict[str, Any]:
        if schema_cls is _DummySchema:
            return {"dummy": DummySectionAlias}
        if schema_cls is _DummySection:
            return {"field": str}
        return original_get_type_hints(schema_cls)

    monkeypatch.setattr(elements_module, "get_type_hints", _fake_get_type_hints)
    monkeypatch.setitem(elements_module.ELEMENT_CONFIG_SCHEMAS, battery.ELEMENT_TYPE, _DummySchema)

    input_fields = battery.adapter.inputs(None)
    sample_field = input_fields[battery.SECTION_STORAGE][battery.CONF_CAPACITY]

    schema_info = get_input_field_schema_info(
        battery.ELEMENT_TYPE,
        {"dummy": {"field": sample_field}},
    )

    assert schema_info["dummy"]["field"].is_optional is False


def test_unwrap_required_type_handles_required_wrappers() -> None:
    """Test _unwrap_required_type returns underlying Required types."""
    assert elements_module._unwrap_required_type(NotRequired[bool]) is bool
    assert elements_module._unwrap_required_type(Required[int]) is int


def test_unwrap_required_type_returns_original_type() -> None:
    """Test _unwrap_required_type returns original type when unwrapped."""
    assert elements_module._unwrap_required_type(str) is str


def test_conforms_to_typed_dict_skips_optional_without_hint() -> None:
    """Test optional keys without hints are ignored when validating."""

    class _Dummy:
        __required_keys__ = frozenset()
        __optional_keys__ = frozenset({"optional"})

    assert elements_module._conforms_to_typed_dict(
        {"optional": 1},
        _Dummy,
        check_optional=True,
    )
