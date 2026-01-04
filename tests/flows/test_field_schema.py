"""Tests for the field_schema utilities."""

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
import pytest
import voluptuous as vol

from custom_components.haeo.const import HAEO_CONFIGURABLE_UNIQUE_ID
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.flows.field_schema import (
    build_configurable_value_schema,
    build_configurable_value_schema_entry,
    convert_entity_selections_to_config,
    get_configurable_entity_id,
    get_configurable_value_defaults,
    get_entity_selection_defaults,
    has_configurable_selection,
    is_configurable_entity,
    number_selector_from_field,
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


@pytest.fixture
def number_field_with_unit() -> InputFieldInfo[NumberEntityDescription]:
    """Return a number field info with unit of measurement."""
    return InputFieldInfo(
        field_name="capacity",
        entity_description=NumberEntityDescription(
            key="capacity",
            translation_key="capacity",
            native_min_value=0.0,
            native_max_value=100.0,
            native_step=0.1,
            native_unit_of_measurement="kWh",
        ),
        output_type=OutputType.ENERGY,
    )


@pytest.fixture
def switch_field_info() -> InputFieldInfo[SwitchEntityDescription]:
    """Return a switch field info for testing."""
    return InputFieldInfo(
        field_name="enabled",
        entity_description=SwitchEntityDescription(
            key="enabled",
            translation_key="enabled",
        ),
        output_type=OutputType.POWER,
        default=True,
    )


class MockConfigSchema:
    """Mock TypedDict-like class for testing config schemas."""

    __optional_keys__ = frozenset({"export_limit"})


# --- Tests for is_configurable_entity ---


def test_is_configurable_entity_with_configurable(mock_hass_context: MagicMock) -> None:
    """is_configurable_entity returns True for the configurable entity."""
    assert is_configurable_entity(TEST_CONFIGURABLE_ENTITY_ID) is True


def test_is_configurable_entity_with_other_entity(mock_hass_context: MagicMock) -> None:
    """is_configurable_entity returns False for other entities."""
    assert is_configurable_entity("sensor.power") is False
    assert is_configurable_entity("number.haeo_import_limit") is False


# --- Tests for has_configurable_selection ---


def test_has_configurable_selection_with_configurable(mock_hass_context: MagicMock) -> None:
    """has_configurable_selection returns True when configurable entity is in selection."""
    assert has_configurable_selection([TEST_CONFIGURABLE_ENTITY_ID]) is True
    assert has_configurable_selection(["sensor.power", TEST_CONFIGURABLE_ENTITY_ID]) is True


def test_has_configurable_selection_without_configurable(mock_hass_context: MagicMock) -> None:
    """has_configurable_selection returns False when configurable entity is not in selection."""
    assert has_configurable_selection([]) is False
    assert has_configurable_selection(["sensor.power"]) is False


# --- Tests for build_configurable_value_schema ---


def test_build_schema_excludes_fields_without_configurable(
    mock_hass_context: MagicMock,
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_configurable_value_schema excludes fields without configurable selection."""
    input_fields = (number_field_info,)
    entity_selections = {"import_limit": ["sensor.power"]}

    schema = build_configurable_value_schema(input_fields, entity_selections)

    # Schema should be empty
    assert len(schema.schema) == 0


def test_build_schema_includes_field_with_configurable(
    mock_hass_context: MagicMock,
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_configurable_value_schema includes fields with configurable selection."""
    input_fields = (number_field_info,)
    entity_selections = {"import_limit": [TEST_CONFIGURABLE_ENTITY_ID]}

    schema = build_configurable_value_schema(input_fields, entity_selections)

    # Schema should include the field
    assert len(schema.schema) == 1


def test_build_schema_excludes_field_with_stored_value(
    mock_hass_context: MagicMock,
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_configurable_value_schema excludes fields with stored configurable values."""
    input_fields = (number_field_info,)
    entity_selections = {"import_limit": [TEST_CONFIGURABLE_ENTITY_ID]}
    current_data: dict[str, Any] = {"import_limit": 50.0}  # Stored value

    schema = build_configurable_value_schema(input_fields, entity_selections, current_data)

    # Schema should be empty - value is already stored
    assert len(schema.schema) == 0


def test_build_schema_includes_field_switching_from_entity(
    mock_hass_context: MagicMock,
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_configurable_value_schema includes fields switching from entity to configurable."""
    input_fields = (number_field_info,)
    entity_selections = {"import_limit": [TEST_CONFIGURABLE_ENTITY_ID]}
    current_data: dict[str, Any] = {"import_limit": ["number.haeo_import_limit"]}  # Entity list

    schema = build_configurable_value_schema(input_fields, entity_selections, current_data)

    # Schema should include the field - user is switching to configurable
    assert len(schema.schema) == 1


def test_build_schema_excludes_field_with_default(
    mock_hass_context: MagicMock,
    number_field_with_default: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_configurable_value_schema excludes fields with defaults and no prior value."""
    input_fields = (number_field_with_default,)
    entity_selections = {"export_limit": [TEST_CONFIGURABLE_ENTITY_ID]}
    current_data: dict[str, Any] = {}  # No stored value but has default

    schema = build_configurable_value_schema(input_fields, entity_selections, current_data)

    # Schema should be empty - default will be used
    assert len(schema.schema) == 0


# --- Tests for get_configurable_entity_id ---


def test_get_configurable_entity_id_raises_when_not_found() -> None:
    """get_configurable_entity_id raises RuntimeError when entity not found."""
    mock_hass = MagicMock()
    mock_registry = MagicMock()
    mock_registry.async_get_entity_id.return_value = None

    with (
        patch("custom_components.haeo.flows.field_schema.async_get_hass", return_value=mock_hass),
        patch("custom_components.haeo.flows.field_schema.er.async_get", return_value=mock_registry),
        pytest.raises(RuntimeError, match="Configurable entity not found"),
    ):
        get_configurable_entity_id()


def test_get_configurable_entity_id_returns_entity_id(mock_hass_context: MagicMock) -> None:
    """get_configurable_entity_id returns the entity ID when found."""
    entity_id = get_configurable_entity_id()
    assert entity_id == TEST_CONFIGURABLE_ENTITY_ID


# --- Tests for number_selector_from_field ---


def test_number_selector_from_field_with_unit(
    number_field_with_unit: InputFieldInfo[NumberEntityDescription],
) -> None:
    """number_selector_from_field includes unit of measurement when present."""
    selector = number_selector_from_field(number_field_with_unit)
    config = selector.config

    assert config["unit_of_measurement"] == "kWh"
    assert config["min"] == 0.0
    assert config["max"] == 100.0


# --- Tests for build_configurable_value_schema_entry ---


def test_build_configurable_value_schema_entry_for_switch(
    switch_field_info: InputFieldInfo[SwitchEntityDescription],
) -> None:
    """build_configurable_value_schema_entry returns BooleanSelector for switch fields."""
    marker, selector = build_configurable_value_schema_entry(switch_field_info)

    # Switch with default should be Optional
    assert isinstance(marker, vol.Optional)
    assert marker.schema == "enabled"
    # Should be a BooleanSelector
    assert selector.__class__.__name__ == "BooleanSelector"


def test_build_configurable_value_schema_entry_for_number_with_default(
    number_field_with_default: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_configurable_value_schema_entry returns Optional for fields with defaults."""
    marker, _ = build_configurable_value_schema_entry(number_field_with_default)

    assert isinstance(marker, vol.Optional)
    assert marker.schema == "export_limit"


def test_build_configurable_value_schema_entry_for_number_without_default(
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_configurable_value_schema_entry returns Required for fields without defaults."""
    marker, _ = build_configurable_value_schema_entry(number_field_info)

    assert isinstance(marker, vol.Required)
    assert marker.schema == "import_limit"


# --- Tests for get_entity_selection_defaults ---


def test_get_entity_selection_defaults_with_invalid_current_value(
    mock_hass_context: MagicMock,
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """get_entity_selection_defaults handles invalid current values gracefully."""
    input_fields = (number_field_info,)
    # Current data has an invalid value (None or some other non-list/non-scalar)
    current_data: dict[str, Any] = {"import_limit": None}

    # Use MockConfigSchema with empty optional keys (all fields required)
    class RequiredFieldSchema:
        __optional_keys__: frozenset[str] = frozenset()

    defaults = get_entity_selection_defaults(input_fields, RequiredFieldSchema(), current_data)

    # Required field with invalid value should default to configurable entity
    assert defaults["import_limit"] == [TEST_CONFIGURABLE_ENTITY_ID]


def test_get_entity_selection_defaults_optional_field_no_default_invalid_value(
    mock_hass_context: MagicMock,
) -> None:
    """get_entity_selection_defaults handles optional fields with no default correctly."""

    class OptionalNoDefaultSchema:
        __optional_keys__: frozenset[str] = frozenset({"optional_field"})

    # Create a field info without default
    optional_no_default = InputFieldInfo(
        field_name="optional_field",
        entity_description=NumberEntityDescription(
            key="optional_field",
            translation_key="optional_field",
            native_min_value=0.0,
            native_max_value=100.0,
        ),
        output_type=OutputType.POWER,
        default=None,  # No default
    )
    input_fields = (optional_no_default,)
    current_data: dict[str, Any] = {"optional_field": None}

    defaults = get_entity_selection_defaults(input_fields, OptionalNoDefaultSchema(), current_data)

    # Optional field without default and invalid value should be empty list
    assert defaults["optional_field"] == []


def test_get_entity_selection_defaults_optional_with_default_invalid_value(
    mock_hass_context: MagicMock,
) -> None:
    """get_entity_selection_defaults for optional field with default uses configurable."""

    class OptionalWithDefaultSchema:
        __optional_keys__: frozenset[str] = frozenset({"optional_with_default"})

    # Create a field info with default
    optional_with_default = InputFieldInfo(
        field_name="optional_with_default",
        entity_description=NumberEntityDescription(
            key="optional_with_default",
            translation_key="optional_with_default",
            native_min_value=0.0,
            native_max_value=100.0,
        ),
        output_type=OutputType.POWER,
        default=50.0,  # Has default
    )
    input_fields = (optional_with_default,)
    current_data: dict[str, Any] = {"optional_with_default": None}

    defaults = get_entity_selection_defaults(input_fields, OptionalWithDefaultSchema(), current_data)

    # Optional field with default and invalid value should use configurable
    assert defaults["optional_with_default"] == [TEST_CONFIGURABLE_ENTITY_ID]


# --- Tests for get_configurable_value_defaults ---


def test_get_configurable_value_defaults_with_scalar_current_value(
    mock_hass_context: MagicMock,
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """get_configurable_value_defaults uses scalar current values."""
    input_fields = (number_field_info,)
    entity_selections = {"import_limit": [TEST_CONFIGURABLE_ENTITY_ID]}
    current_data: dict[str, Any] = {"import_limit": 42.0}

    defaults = get_configurable_value_defaults(input_fields, entity_selections, current_data)

    assert defaults["import_limit"] == 42.0


def test_get_configurable_value_defaults_with_boolean_current_value(
    mock_hass_context: MagicMock,
    switch_field_info: InputFieldInfo[SwitchEntityDescription],
) -> None:
    """get_configurable_value_defaults handles boolean current values."""
    input_fields = (switch_field_info,)
    entity_selections = {"enabled": [TEST_CONFIGURABLE_ENTITY_ID]}
    current_data: dict[str, Any] = {"enabled": False}

    defaults = get_configurable_value_defaults(input_fields, entity_selections, current_data)

    assert defaults["enabled"] is False


def test_get_configurable_value_defaults_with_int_current_value(
    mock_hass_context: MagicMock,
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """get_configurable_value_defaults handles int current values."""
    input_fields = (number_field_info,)
    entity_selections = {"import_limit": [TEST_CONFIGURABLE_ENTITY_ID]}
    current_data: dict[str, Any] = {"import_limit": 50}

    defaults = get_configurable_value_defaults(input_fields, entity_selections, current_data)

    assert defaults["import_limit"] == 50


def test_get_configurable_value_defaults_falls_back_to_field_default(
    mock_hass_context: MagicMock,
    number_field_with_default: InputFieldInfo[NumberEntityDescription],
) -> None:
    """get_configurable_value_defaults uses field default when current value is not scalar."""
    input_fields = (number_field_with_default,)
    entity_selections = {"export_limit": [TEST_CONFIGURABLE_ENTITY_ID]}
    # Current value is a list (entity links), not a scalar
    current_data: dict[str, Any] = {"export_limit": ["sensor.something"]}

    defaults = get_configurable_value_defaults(input_fields, entity_selections, current_data)

    # Should fall back to field default
    assert defaults["export_limit"] == 100.0


def test_get_configurable_value_defaults_uses_field_default_no_current_data(
    mock_hass_context: MagicMock,
    number_field_with_default: InputFieldInfo[NumberEntityDescription],
) -> None:
    """get_configurable_value_defaults uses field default when no current data."""
    input_fields = (number_field_with_default,)
    entity_selections = {"export_limit": [TEST_CONFIGURABLE_ENTITY_ID]}

    defaults = get_configurable_value_defaults(input_fields, entity_selections)

    assert defaults["export_limit"] == 100.0


# --- Tests for convert_entity_selections_to_config ---


def test_convert_entity_selections_to_config_empty_selection_with_default(
    mock_hass_context: MagicMock,
    number_field_with_default: InputFieldInfo[NumberEntityDescription],
) -> None:
    """convert_entity_selections_to_config applies default for empty selections."""
    entity_selections: dict[str, list[str]] = {"export_limit": []}
    configurable_values: dict[str, Any] = {}
    input_fields = (number_field_with_default,)

    config = convert_entity_selections_to_config(entity_selections, configurable_values, input_fields)

    # Empty selection should use the field's default value
    assert config["export_limit"] == 100.0


def test_convert_entity_selections_to_config_empty_selection_no_default(
    mock_hass_context: MagicMock,
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """convert_entity_selections_to_config omits fields with empty selection and no default."""
    entity_selections: dict[str, list[str]] = {"import_limit": []}
    configurable_values: dict[str, Any] = {}
    input_fields = (number_field_info,)

    config = convert_entity_selections_to_config(entity_selections, configurable_values, input_fields)

    # Empty selection without default should be omitted
    assert "import_limit" not in config


def test_convert_entity_selections_to_config_with_configurable_value(
    mock_hass_context: MagicMock,
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """convert_entity_selections_to_config uses configurable value from step 2."""
    entity_selections = {"import_limit": [TEST_CONFIGURABLE_ENTITY_ID]}
    configurable_values: dict[str, Any] = {"import_limit": 75.0}
    input_fields = (number_field_info,)

    config = convert_entity_selections_to_config(entity_selections, configurable_values, input_fields)

    assert config["import_limit"] == 75.0


def test_convert_entity_selections_to_config_with_real_entities(
    mock_hass_context: MagicMock,
    number_field_info: InputFieldInfo[NumberEntityDescription],
) -> None:
    """convert_entity_selections_to_config keeps real entity lists."""
    entity_selections = {"import_limit": ["sensor.power1", "sensor.power2"]}
    configurable_values: dict[str, Any] = {}
    input_fields = (number_field_info,)

    config = convert_entity_selections_to_config(entity_selections, configurable_values, input_fields)

    assert config["import_limit"] == ["sensor.power1", "sensor.power2"]
