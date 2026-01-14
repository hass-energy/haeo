"""Tests for flows/field_schema.py utilities."""

from typing import Any

from homeassistant.components.number import NumberEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import BooleanSelector, NumberSelector
import pytest

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.elements.input_fields import InputFieldDefaults, InputFieldInfo
from custom_components.haeo.flows.field_schema import (
    boolean_selector_from_field,
    convert_entity_selections_to_config,
    extract_non_entity_fields,
    get_haeo_input_entity_ids,
    is_haeo_input_entity,
    number_selector_from_field,
)
from custom_components.haeo.model.const import OutputType

# --- Fixtures ---


@pytest.fixture
def number_field() -> InputFieldInfo[NumberEntityDescription]:
    """Create a number input field for testing."""
    return InputFieldInfo(
        field_name="test_field",
        entity_description=NumberEntityDescription(
            key="test_field",
            name="Test Field",
            native_min_value=0.0,
            native_max_value=100.0,
            native_step=1.0,
            native_unit_of_measurement="kW",
        ),
        output_type=OutputType.POWER,
        defaults=InputFieldDefaults(mode="value", value=50.0),
    )


# --- Tests for boolean_selector_from_field ---


def test_boolean_selector_from_field_returns_boolean_selector() -> None:
    """Boolean selector is created."""
    selector = boolean_selector_from_field()
    assert isinstance(selector, BooleanSelector)


# --- Tests for number_selector_from_field ---


def test_number_selector_from_field_creates_selector(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Number selector is created with correct config."""
    selector = number_selector_from_field(number_field)
    assert isinstance(selector, NumberSelector)


def test_number_selector_from_field_without_min_max_values() -> None:
    """Number selector is created when min/max values are None."""
    field = InputFieldInfo(
        field_name="price_field",
        entity_description=NumberEntityDescription(
            key="price_field",
            name="Price Field",
            native_min_value=None,
            native_max_value=None,
            native_step=0.01,
        ),
        output_type=OutputType.PRICE,
    )
    selector = number_selector_from_field(field)
    assert isinstance(selector, NumberSelector)
    # Config should not include min/max when None
    config = selector.config
    assert "min" not in config
    assert "max" not in config


def test_number_selector_from_field_without_unit() -> None:
    """Number selector is created without unit of measurement."""
    field = InputFieldInfo(
        field_name="efficiency",
        entity_description=NumberEntityDescription(
            key="efficiency",
            name="Efficiency",
            native_min_value=0.0,
            native_max_value=100.0,
            native_step=1.0,
            native_unit_of_measurement=None,
        ),
        output_type=OutputType.EFFICIENCY,
    )
    selector = number_selector_from_field(field)
    assert isinstance(selector, NumberSelector)


# --- Tests for is_haeo_input_entity ---


def test_is_haeo_input_entity_returns_false_for_nonexistent(hass: HomeAssistant) -> None:
    """is_haeo_input_entity returns False for non-existent entity."""
    result = is_haeo_input_entity("sensor.does_not_exist")
    assert result is False


def test_is_haeo_input_entity_returns_false_for_non_haeo_platform(hass: HomeAssistant) -> None:
    """is_haeo_input_entity returns False for entity from different platform."""
    registry = er.async_get(hass)
    registry.async_get_or_create(
        domain="sensor",
        platform="other_integration",
        unique_id="test_sensor_123",
        suggested_object_id="other_sensor",
    )
    result = is_haeo_input_entity("sensor.other_sensor")
    assert result is False


def test_is_haeo_input_entity_returns_true_for_haeo_input_entity(hass: HomeAssistant) -> None:
    """is_haeo_input_entity returns True for HAEO input entity with correct unique_id pattern."""
    registry = er.async_get(hass)
    entity = registry.async_get_or_create(
        domain="number",
        platform=DOMAIN,
        unique_id="entry_id_subentry_id_field_name",  # Pattern: entry_id_subentry_id_field_name
        suggested_object_id="haeo_test_entity",
    )
    result = is_haeo_input_entity(entity.entity_id)
    assert result is True


def test_is_haeo_input_entity_returns_false_for_haeo_without_underscores(hass: HomeAssistant) -> None:
    """is_haeo_input_entity returns False for HAEO entity without enough underscores."""
    registry = er.async_get(hass)
    entity = registry.async_get_or_create(
        domain="number",
        platform=DOMAIN,
        unique_id="simple",  # No underscores
        suggested_object_id="haeo_simple",
    )
    result = is_haeo_input_entity(entity.entity_id)
    assert result is False


# --- Tests for get_haeo_input_entity_ids ---


def test_get_haeo_input_entity_ids_returns_empty_for_no_haeo_entities(hass: HomeAssistant) -> None:
    """get_haeo_input_entity_ids returns empty list when no HAEO input entities exist."""
    registry = er.async_get(hass)
    # Create non-HAEO entities only
    registry.async_get_or_create(
        domain="sensor",
        platform="other_integration",
        unique_id="external_sensor",
        suggested_object_id="external",
    )
    result = get_haeo_input_entity_ids()
    # Result should not include non-HAEO entities
    assert "sensor.external" not in result


def test_get_haeo_input_entity_ids_includes_haeo_input_entities(hass: HomeAssistant) -> None:
    """get_haeo_input_entity_ids includes HAEO input entities with correct pattern."""
    registry = er.async_get(hass)
    # Create HAEO input entity with proper pattern
    haeo_entity = registry.async_get_or_create(
        domain="number",
        platform=DOMAIN,
        unique_id="entry_id_subentry_id_capacity",
        suggested_object_id="haeo_battery_capacity",
    )
    # Create non-HAEO entity
    registry.async_get_or_create(
        domain="sensor",
        platform="other_integration",
        unique_id="external",
        suggested_object_id="external_sensor",
    )
    result = get_haeo_input_entity_ids()
    assert haeo_entity.entity_id in result
    assert "sensor.external_sensor" not in result


def test_get_haeo_input_entity_ids_excludes_haeo_without_pattern(hass: HomeAssistant) -> None:
    """get_haeo_input_entity_ids excludes HAEO entities without input pattern."""
    registry = er.async_get(hass)
    # Create HAEO entity without proper pattern (like configurable sentinel)
    haeo_entity = registry.async_get_or_create(
        domain=DOMAIN,
        platform=DOMAIN,
        unique_id="simple",  # Single component, not entry_id_subentry_id_field
        suggested_object_id="haeo_simple",
    )
    result = get_haeo_input_entity_ids()
    assert haeo_entity.entity_id not in result


# --- Tests for extract_non_entity_fields ---


def test_extract_non_entity_fields_extracts_non_list_values() -> None:
    """extract_non_entity_fields extracts non-list values from step data."""
    step1_data = {
        "name": "Test Element",
        "connection": "main_bus",
        "import_price": ["sensor.price"],  # List - should be excluded
        "export_price": ["sensor.export"],  # List - should be excluded
    }
    result = extract_non_entity_fields(step1_data)
    assert result == {"name": "Test Element", "connection": "main_bus"}


def test_extract_non_entity_fields_respects_exclude_keys() -> None:
    """extract_non_entity_fields excludes specified keys."""
    step1_data = {
        "name": "Test Element",
        "connection": "main_bus",
        "capacity": 10.5,
    }
    result = extract_non_entity_fields(step1_data, exclude_keys=("name", "connection"))
    assert result == {"capacity": 10.5}


def test_extract_non_entity_fields_returns_empty_for_all_lists() -> None:
    """extract_non_entity_fields returns empty dict when all values are lists."""
    step1_data = {
        "import_price": ["sensor.price"],
        "export_price": ["sensor.export"],
    }
    result = extract_non_entity_fields(step1_data)
    assert result == {}


# --- Tests for convert_entity_selections_to_config ---


def test_convert_empty_selection_omitted() -> None:
    """Empty entity selection is omitted from config."""
    entity_selections: dict[str, list[str]] = {"field1": []}
    configurable_values: dict[str, Any] = {}

    result = convert_entity_selections_to_config(entity_selections, configurable_values)

    assert "field1" not in result


def test_convert_configurable_entity_uses_configurable_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configurable entity selection uses value from configurable_values."""
    monkeypatch.setattr(
        "custom_components.haeo.flows.field_schema.is_configurable_entity",
        lambda entity_id: entity_id == "number.haeo_configure_power",
    )
    entity_selections = {"power": ["number.haeo_configure_power"]}
    configurable_values: dict[str, Any] = {"power": 10.5}

    result = convert_entity_selections_to_config(entity_selections, configurable_values)

    assert result["power"] == 10.5


def test_convert_configurable_entity_without_value_omitted(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configurable entity without value in configurable_values is omitted."""
    monkeypatch.setattr(
        "custom_components.haeo.flows.field_schema.is_configurable_entity",
        lambda entity_id: entity_id == "number.haeo_configure_power",
    )
    entity_selections = {"power": ["number.haeo_configure_power"]}
    configurable_values: dict[str, Any] = {}

    result = convert_entity_selections_to_config(entity_selections, configurable_values)

    assert "power" not in result


def test_convert_external_entity_single_stored_as_string() -> None:
    """Single external entity is stored as string."""
    entity_selections = {"power": ["sensor.grid_power"]}
    configurable_values: dict[str, Any] = {}

    result = convert_entity_selections_to_config(entity_selections, configurable_values)

    assert result["power"] == "sensor.grid_power"


def test_convert_external_entity_multiple_stored_as_list() -> None:
    """Multiple external entities are stored as list."""
    entity_selections = {"power": ["sensor.power1", "sensor.power2"]}
    configurable_values: dict[str, Any] = {}

    result = convert_entity_selections_to_config(entity_selections, configurable_values)

    assert result["power"] == ["sensor.power1", "sensor.power2"]


def test_convert_self_referential_entity_preserves_float(monkeypatch: pytest.MonkeyPatch) -> None:
    """Self-referential entity selection preserves float from current_data."""
    monkeypatch.setattr(
        "custom_components.haeo.flows.field_schema.resolve_configurable_entity_id",
        lambda _entry_id, _subentry_id, _field_name: "number.haeo_entry1_sub1_capacity",
    )
    entity_selections = {"capacity": ["number.haeo_entry1_sub1_capacity"]}
    configurable_values: dict[str, Any] = {}
    current_data: dict[str, Any] = {"capacity": 13.5}

    result = convert_entity_selections_to_config(
        entity_selections,
        configurable_values,
        current_data=current_data,
        entry_id="entry1",
        subentry_id="sub1",
    )

    assert result["capacity"] == 13.5


def test_convert_self_referential_entity_preserves_int(monkeypatch: pytest.MonkeyPatch) -> None:
    """Self-referential entity selection preserves int from current_data."""
    monkeypatch.setattr(
        "custom_components.haeo.flows.field_schema.resolve_configurable_entity_id",
        lambda _entry_id, _subentry_id, _field_name: "number.haeo_entry1_sub1_capacity",
    )
    entity_selections = {"capacity": ["number.haeo_entry1_sub1_capacity"]}
    configurable_values: dict[str, Any] = {}
    current_data: dict[str, Any] = {"capacity": 10}

    result = convert_entity_selections_to_config(
        entity_selections,
        configurable_values,
        current_data=current_data,
        entry_id="entry1",
        subentry_id="sub1",
    )

    assert result["capacity"] == 10


def test_convert_self_referential_entity_preserves_bool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Self-referential entity selection preserves boolean from current_data."""
    monkeypatch.setattr(
        "custom_components.haeo.flows.field_schema.resolve_configurable_entity_id",
        lambda _entry_id, _subentry_id, _field_name: "switch.haeo_entry1_sub1_enabled",
    )
    entity_selections = {"enabled": ["switch.haeo_entry1_sub1_enabled"]}
    configurable_values: dict[str, Any] = {}
    current_data: dict[str, Any] = {"enabled": True}

    result = convert_entity_selections_to_config(
        entity_selections,
        configurable_values,
        current_data=current_data,
        entry_id="entry1",
        subentry_id="sub1",
    )

    assert result["enabled"] is True


def test_convert_self_referential_without_current_data_raises_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Self-referential entity without current_data raises HomeAssistantError."""
    monkeypatch.setattr(
        "custom_components.haeo.flows.field_schema.resolve_configurable_entity_id",
        lambda _entry_id, _subentry_id, _field_name: "number.haeo_entry1_sub1_capacity",
    )
    entity_selections = {"capacity": ["number.haeo_entry1_sub1_capacity"]}
    configurable_values: dict[str, Any] = {}

    with pytest.raises(HomeAssistantError) as exc_info:
        convert_entity_selections_to_config(
            entity_selections,
            configurable_values,
            current_data=None,
            entry_id="entry1",
            subentry_id="sub1",
        )

    assert exc_info.value.translation_key == "self_referential_no_current_data"
    assert exc_info.value.translation_placeholders == {"field": "capacity"}


def test_convert_self_referential_with_non_scalar_raises_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Self-referential entity with non-scalar value raises HomeAssistantError."""
    monkeypatch.setattr(
        "custom_components.haeo.flows.field_schema.resolve_configurable_entity_id",
        lambda _entry_id, _subentry_id, _field_name: "number.haeo_entry1_sub1_capacity",
    )
    entity_selections = {"capacity": ["number.haeo_entry1_sub1_capacity"]}
    configurable_values: dict[str, Any] = {}
    current_data: dict[str, Any] = {"capacity": ["sensor.external"]}  # List, not scalar

    with pytest.raises(HomeAssistantError) as exc_info:
        convert_entity_selections_to_config(
            entity_selections,
            configurable_values,
            current_data=current_data,
            entry_id="entry1",
            subentry_id="sub1",
        )

    assert exc_info.value.translation_key == "self_referential_invalid_value"
    assert exc_info.value.translation_placeholders == {"field": "capacity", "value_type": "list"}


def test_convert_other_haeo_entity_stored_as_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    """Other HAEO entity (not self-referential) is stored as entity reference."""
    monkeypatch.setattr(
        "custom_components.haeo.flows.field_schema.resolve_configurable_entity_id",
        lambda _entry_id, _subentry_id, _field_name: "number.haeo_entry1_sub1_capacity",
    )
    # This is a DIFFERENT HAEO entity (from another element)
    entity_selections = {"capacity": ["number.haeo_entry1_other_sub_capacity"]}
    configurable_values: dict[str, Any] = {}
    current_data: dict[str, Any] = {"capacity": 13.5}

    result = convert_entity_selections_to_config(
        entity_selections,
        configurable_values,
        current_data=current_data,
        entry_id="entry1",
        subentry_id="sub1",
    )

    # Should be stored as entity reference, NOT preserve scalar
    assert result["capacity"] == "number.haeo_entry1_other_sub_capacity"


def test_convert_no_entry_id_treats_as_external() -> None:
    """Without entry_id, any entity is treated as external (stored as reference)."""
    entity_selections = {"capacity": ["number.haeo_battery_capacity"]}
    configurable_values: dict[str, Any] = {}
    current_data: dict[str, Any] = {"capacity": 13.5}

    result = convert_entity_selections_to_config(
        entity_selections,
        configurable_values,
        current_data=current_data,
        # No entry_id or subentry_id
    )

    # Without entry_id, can't determine self-reference, so store as entity
    assert result["capacity"] == "number.haeo_battery_capacity"


def test_convert_self_referential_field_not_in_current_data_raises_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Self-referential entity with field not in current_data raises HomeAssistantError."""
    monkeypatch.setattr(
        "custom_components.haeo.flows.field_schema.resolve_configurable_entity_id",
        lambda _entry_id, _subentry_id, _field_name: "number.haeo_entry1_sub1_capacity",
    )
    entity_selections = {"capacity": ["number.haeo_entry1_sub1_capacity"]}
    configurable_values: dict[str, Any] = {}
    current_data: dict[str, Any] = {"other_field": 10.0}

    with pytest.raises(HomeAssistantError) as exc_info:
        convert_entity_selections_to_config(
            entity_selections,
            configurable_values,
            current_data=current_data,
            entry_id="entry1",
            subentry_id="sub1",
        )

    assert exc_info.value.translation_key == "self_referential_field_missing"
    assert exc_info.value.translation_placeholders == {"field": "capacity"}
