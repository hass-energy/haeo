"""Tests for the field_schema utilities."""

from typing import Any

from homeassistant.components.number import NumberEntityDescription
import pytest

from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.flows.field_schema import (
    build_constant_value_schema,
    can_reuse_constant_values,
    has_constant_selection,
    is_constant_entity,
)
from custom_components.haeo.model.const import OutputType


@pytest.fixture
def number_field_info() -> InputFieldInfo[NumberEntityDescription]:
    """Return a number field info for testing."""
    return InputFieldInfo(
        field_name="import_limit",
        entity_description=NumberEntityDescription(
            key="import_limit",
            translation_key="import_limit",
            native_min_value=0.0,
            native_max_value=1000.0,
            native_step=0.1,
        ),
        output_type=OutputType.POWER,
    )


@pytest.fixture
def number_field_with_default() -> InputFieldInfo[NumberEntityDescription]:
    """Return a number field info with a default value."""
    return InputFieldInfo(
        field_name="export_limit",
        entity_description=NumberEntityDescription(
            key="export_limit",
            translation_key="export_limit",
            native_min_value=0.0,
            native_max_value=1000.0,
            native_step=0.1,
        ),
        output_type=OutputType.POWER,
        default=100.0,
    )


# --- Tests for is_constant_entity ---


def test_is_constant_entity_with_constant() -> None:
    """is_constant_entity returns True for haeo.constant."""
    assert is_constant_entity("haeo.constant") is True


def test_is_constant_entity_with_other_entity() -> None:
    """is_constant_entity returns False for other entities."""
    assert is_constant_entity("sensor.power") is False
    assert is_constant_entity("number.haeo_import_limit") is False


# --- Tests for has_constant_selection ---


def test_has_constant_selection_with_constant() -> None:
    """has_constant_selection returns True when constant is in selection."""
    assert has_constant_selection(["haeo.constant"]) is True
    assert has_constant_selection(["sensor.power", "haeo.constant"]) is True


def test_has_constant_selection_without_constant() -> None:
    """has_constant_selection returns False when constant is not in selection."""
    assert has_constant_selection([]) is False
    assert has_constant_selection(["sensor.power"]) is False


# --- Tests for can_reuse_constant_values ---


def test_can_reuse_when_no_constant_selected(
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """can_reuse_constant_values returns True when no constant is selected."""
    input_fields = (number_field_info,)
    entity_selections = {"import_limit": ["sensor.power"]}
    current_data: dict[str, Any] = {"import_limit": ["sensor.power"]}

    assert can_reuse_constant_values(input_fields, entity_selections, current_data) is True


def test_can_reuse_when_constant_has_stored_value(
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """can_reuse_constant_values returns True when constant value is stored."""
    input_fields = (number_field_info,)
    entity_selections = {"import_limit": ["haeo.constant"]}
    current_data: dict[str, Any] = {"import_limit": 50.0}  # Stored constant value

    assert can_reuse_constant_values(input_fields, entity_selections, current_data) is True


def test_cannot_reuse_when_switching_from_entity_to_constant(
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """can_reuse_constant_values returns False when switching from entity to constant."""
    input_fields = (number_field_info,)
    entity_selections = {"import_limit": ["haeo.constant"]}
    current_data: dict[str, Any] = {"import_limit": ["number.haeo_import_limit"]}  # Entity list

    # User is switching TO constant from entity - need to ask for value
    assert can_reuse_constant_values(input_fields, entity_selections, current_data) is False


def test_cannot_reuse_when_no_value_and_no_default(
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """can_reuse_constant_values returns False when no value and no default."""
    input_fields = (number_field_info,)
    entity_selections = {"import_limit": ["haeo.constant"]}
    current_data: dict[str, Any] = {}  # No stored value

    # No stored value and no default - need user input
    assert can_reuse_constant_values(input_fields, entity_selections, current_data) is False


def test_can_reuse_when_field_has_default(
    number_field_with_default: InputFieldInfo[NumberEntityDescription],
) -> None:
    """can_reuse_constant_values returns True when field has default."""
    input_fields = (number_field_with_default,)
    entity_selections = {"export_limit": ["haeo.constant"]}
    current_data: dict[str, Any] = {}  # No stored value but has default

    assert can_reuse_constant_values(input_fields, entity_selections, current_data) is True


# --- Tests for build_constant_value_schema ---


def test_build_schema_excludes_fields_without_constant(
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_constant_value_schema excludes fields without constant selection."""
    input_fields = (number_field_info,)
    entity_selections = {"import_limit": ["sensor.power"]}

    schema = build_constant_value_schema(input_fields, entity_selections)

    # Schema should be empty
    assert len(schema.schema) == 0


def test_build_schema_includes_field_with_constant(
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_constant_value_schema includes fields with constant selection."""
    input_fields = (number_field_info,)
    entity_selections = {"import_limit": ["haeo.constant"]}

    schema = build_constant_value_schema(input_fields, entity_selections)

    # Schema should include the field
    assert len(schema.schema) == 1


def test_build_schema_excludes_field_with_stored_value(
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_constant_value_schema excludes fields with stored constant values."""
    input_fields = (number_field_info,)
    entity_selections = {"import_limit": ["haeo.constant"]}
    current_data: dict[str, Any] = {"import_limit": 50.0}  # Stored value

    schema = build_constant_value_schema(input_fields, entity_selections, current_data)

    # Schema should be empty - value is already stored
    assert len(schema.schema) == 0


def test_build_schema_includes_field_switching_from_entity(
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_constant_value_schema includes fields switching from entity to constant."""
    input_fields = (number_field_info,)
    entity_selections = {"import_limit": ["haeo.constant"]}
    current_data: dict[str, Any] = {"import_limit": ["number.haeo_import_limit"]}  # Entity list

    schema = build_constant_value_schema(input_fields, entity_selections, current_data)

    # Schema should include the field - user is switching to constant
    assert len(schema.schema) == 1


def test_build_schema_excludes_field_with_default(
    number_field_with_default: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_constant_value_schema excludes fields with defaults and no prior value."""
    input_fields = (number_field_with_default,)
    entity_selections = {"export_limit": ["haeo.constant"]}
    current_data: dict[str, Any] = {}  # No stored value but has default

    schema = build_constant_value_schema(input_fields, entity_selections, current_data)

    # Schema should be empty - default will be used
    assert len(schema.schema) == 0
