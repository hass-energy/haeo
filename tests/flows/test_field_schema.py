"""Tests for flows/field_schema.py utilities."""

from typing import Any

from homeassistant.components.number import NumberEntityDescription
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import BooleanSelector, NumberSelector
import pytest

from custom_components.haeo.elements.input_fields import InputFieldDefaults, InputFieldInfo
from custom_components.haeo.flows.field_schema import (
    boolean_selector_from_field,
    convert_entity_selections_to_config,
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
