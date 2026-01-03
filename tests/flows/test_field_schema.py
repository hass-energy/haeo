"""Tests for the field_schema utilities."""

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

from homeassistant.components.number import NumberEntityDescription
import pytest

from custom_components.haeo.const import HAEO_CONFIGURABLE_UNIQUE_ID
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.flows.field_schema import (
    build_constant_value_schema,
    has_constant_selection,
    is_constant_entity,
)
from custom_components.haeo.model.const import OutputType

# Test entity ID for the configurable entity
TEST_CONFIGURABLE_ENTITY_ID = "haeo.configurable_entity"


@pytest.fixture
def mock_registry() -> MagicMock:
    """Return a mock entity registry."""
    return MagicMock()


@pytest.fixture
def mock_hass_context(mock_registry: MagicMock) -> Generator[MagicMock]:
    """Set up mock hass context that recognizes the configurable entity.

    This patches both async_get_hass() and the entity registry to simulate
    the runtime environment where the configurable entity exists.
    """
    # Create a mock registry entry for the configurable entity
    mock_entry = MagicMock()
    mock_entry.unique_id = HAEO_CONFIGURABLE_UNIQUE_ID

    def async_get(entity_id: str) -> MagicMock | None:
        if entity_id == TEST_CONFIGURABLE_ENTITY_ID:
            return mock_entry
        return None

    mock_registry.async_get = async_get
    mock_registry.async_get_entity_id.return_value = TEST_CONFIGURABLE_ENTITY_ID

    mock_hass = MagicMock()

    with (
        patch("custom_components.haeo.flows.field_schema.async_get_hass", return_value=mock_hass),
        patch("custom_components.haeo.flows.field_schema.er.async_get", return_value=mock_registry),
    ):
        yield mock_hass


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


def test_is_constant_entity_with_constant(mock_hass_context: MagicMock) -> None:
    """is_constant_entity returns True for the configurable entity."""
    assert is_constant_entity(TEST_CONFIGURABLE_ENTITY_ID) is True


def test_is_constant_entity_with_other_entity(mock_hass_context: MagicMock) -> None:
    """is_constant_entity returns False for other entities."""
    assert is_constant_entity("sensor.power") is False
    assert is_constant_entity("number.haeo_import_limit") is False


# --- Tests for has_constant_selection ---


def test_has_constant_selection_with_constant(mock_hass_context: MagicMock) -> None:
    """has_constant_selection returns True when constant is in selection."""
    assert has_constant_selection([TEST_CONFIGURABLE_ENTITY_ID]) is True
    assert has_constant_selection(["sensor.power", TEST_CONFIGURABLE_ENTITY_ID]) is True


def test_has_constant_selection_without_constant(mock_hass_context: MagicMock) -> None:
    """has_constant_selection returns False when constant is not in selection."""
    assert has_constant_selection([]) is False
    assert has_constant_selection(["sensor.power"]) is False


# --- Tests for build_constant_value_schema ---


def test_build_schema_excludes_fields_without_constant(
    mock_hass_context: MagicMock,
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_constant_value_schema excludes fields without constant selection."""
    input_fields = (number_field_info,)
    entity_selections = {"import_limit": ["sensor.power"]}

    schema = build_constant_value_schema(input_fields, entity_selections)

    # Schema should be empty
    assert len(schema.schema) == 0


def test_build_schema_includes_field_with_constant(
    mock_hass_context: MagicMock,
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_constant_value_schema includes fields with constant selection."""
    input_fields = (number_field_info,)
    entity_selections = {"import_limit": [TEST_CONFIGURABLE_ENTITY_ID]}

    schema = build_constant_value_schema(input_fields, entity_selections)

    # Schema should include the field
    assert len(schema.schema) == 1


def test_build_schema_excludes_field_with_stored_value(
    mock_hass_context: MagicMock,
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_constant_value_schema excludes fields with stored constant values."""
    input_fields = (number_field_info,)
    entity_selections = {"import_limit": [TEST_CONFIGURABLE_ENTITY_ID]}
    current_data: dict[str, Any] = {"import_limit": 50.0}  # Stored value

    schema = build_constant_value_schema(input_fields, entity_selections, current_data)

    # Schema should be empty - value is already stored
    assert len(schema.schema) == 0


def test_build_schema_includes_field_switching_from_entity(
    mock_hass_context: MagicMock,
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_constant_value_schema includes fields switching from entity to constant."""
    input_fields = (number_field_info,)
    entity_selections = {"import_limit": [TEST_CONFIGURABLE_ENTITY_ID]}
    current_data: dict[str, Any] = {"import_limit": ["number.haeo_import_limit"]}  # Entity list

    schema = build_constant_value_schema(input_fields, entity_selections, current_data)

    # Schema should include the field - user is switching to constant
    assert len(schema.schema) == 1


def test_build_schema_excludes_field_with_default(
    mock_hass_context: MagicMock,
    number_field_with_default: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_constant_value_schema excludes fields with defaults and no prior value."""
    input_fields = (number_field_with_default,)
    entity_selections = {"export_limit": [TEST_CONFIGURABLE_ENTITY_ID]}
    current_data: dict[str, Any] = {}  # No stored value but has default

    schema = build_constant_value_schema(input_fields, entity_selections, current_data)

    # Schema should be empty - default will be used
    assert len(schema.schema) == 0
