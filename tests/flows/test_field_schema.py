"""Tests for flows/field_schema.py utilities."""

from typing import Any

from homeassistant.components.number import NumberEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import BooleanSelector, NumberSelector
import pytest
import voluptuous as vol

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.sections import SECTION_COMMON
from custom_components.haeo.elements.field_schema import FieldSchemaInfo
from custom_components.haeo.elements.input_fields import InputFieldDefaults, InputFieldInfo
from custom_components.haeo.flows.field_schema import (
    CHOICE_CONSTANT,
    CHOICE_ENTITY,
    CHOICE_NONE,
    NormalizingChooseSelector,
    SectionDefinition,
    boolean_selector_from_field,
    build_choose_field_entries,
    build_choose_selector,
    build_entity_selector,
    build_section_schema,
    build_sectioned_choose_defaults,
    build_sectioned_choose_schema,
    convert_choose_data_to_config,
    convert_sectioned_choose_data_to_config,
    get_choose_default,
    get_haeo_input_entity_ids,
    get_preferred_choice,
    is_valid_choose_value,
    number_selector_from_field,
    preprocess_choose_selector_input,
    preprocess_sectioned_choose_input,
    resolve_haeo_input_entity_id,
    validate_choose_fields,
    validate_sectioned_choose_fields,
)
from custom_components.haeo.schema import (
    ConstantValue,
    EntityValue,
    NoneValue,
    as_constant_value,
    as_entity_value,
    as_none_value,
)

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


def _field_map(*fields: InputFieldInfo[Any]) -> dict[str, InputFieldInfo[Any]]:
    """Build an input field mapping keyed by field name."""
    return {field.field_name: field for field in fields}


ALLOWED_CHOICES_REQUIRED = frozenset({CHOICE_ENTITY, CHOICE_CONSTANT})
ALLOWED_CHOICES_OPTIONAL = frozenset({CHOICE_ENTITY, CHOICE_CONSTANT, CHOICE_NONE})


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


# --- Tests for build_choose_selector ---


def test_build_choose_selector_creates_normalizing_choose_selector(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """NormalizingChooseSelector is created with entity and constant choices."""
    selector = build_choose_selector(number_field, allowed_choices=ALLOWED_CHOICES_REQUIRED)
    assert isinstance(selector, NormalizingChooseSelector)


def test_build_choose_selector_entity_first_by_default(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Entity choice appears first when preferred_choice is entity."""
    selector = build_choose_selector(
        number_field,
        allowed_choices=ALLOWED_CHOICES_REQUIRED,
        preferred_choice=CHOICE_ENTITY,
    )
    config = selector.config
    choices_keys = list(config["choices"].keys())
    assert choices_keys[0] == CHOICE_ENTITY
    assert choices_keys[1] == CHOICE_CONSTANT


def test_build_choose_selector_constant_first_when_preferred(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Constant choice appears first when preferred_choice is constant."""
    selector = build_choose_selector(
        number_field,
        allowed_choices=ALLOWED_CHOICES_REQUIRED,
        preferred_choice=CHOICE_CONSTANT,
    )
    config = selector.config
    choices_keys = list(config["choices"].keys())
    assert choices_keys[0] == CHOICE_CONSTANT
    assert choices_keys[1] == CHOICE_ENTITY


# --- Tests for get_preferred_choice ---


def test_get_preferred_choice_returns_entity_by_default() -> None:
    """get_preferred_choice returns entity when no current_data or defaults."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
        defaults=None,
    )
    result = get_preferred_choice(field, allowed_choices=ALLOWED_CHOICES_REQUIRED)
    assert result == CHOICE_ENTITY


def test_get_preferred_choice_returns_constant_for_value_defaults() -> None:
    """get_preferred_choice returns constant when defaults.mode is value."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
        defaults=InputFieldDefaults(mode="value", value=10.0),
    )
    result = get_preferred_choice(field, allowed_choices=ALLOWED_CHOICES_REQUIRED)
    assert result == CHOICE_CONSTANT


def test_get_preferred_choice_returns_entity_for_entity_defaults() -> None:
    """get_preferred_choice returns entity when defaults.mode is entity."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
        defaults=InputFieldDefaults(mode="entity"),
    )
    result = get_preferred_choice(field, allowed_choices=ALLOWED_CHOICES_REQUIRED)
    assert result == CHOICE_ENTITY


def test_get_preferred_choice_uses_current_data_entity_value() -> None:
    """get_preferred_choice returns entity when current_data has schema entity value."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
    )
    current_data = {SECTION_COMMON: {"power": as_entity_value(["sensor.power"])}}
    result = get_preferred_choice(field, current_data, allowed_choices=ALLOWED_CHOICES_REQUIRED)
    assert result == CHOICE_ENTITY


def test_get_preferred_choice_uses_current_data_entity_list() -> None:
    """get_preferred_choice returns entity when current_data has entity list.

    This covers the case where multiple=True is used on EntitySelector,
    which stores entity IDs as a list (e.g., for chained sensors).
    """
    field = InputFieldInfo(
        field_name="price_source_target",
        entity_description=NumberEntityDescription(
            key="price_source_target",
            name="Price Source Target",
        ),
        output_type=OutputType.PRICE,
    )
    current_data = {
        SECTION_COMMON: {
            "price_source_target": as_entity_value(["sensor.current_price", "sensor.forecast_price"]),
        }
    }
    result = get_preferred_choice(field, current_data, allowed_choices=ALLOWED_CHOICES_REQUIRED)
    assert result == CHOICE_ENTITY


def test_get_preferred_choice_uses_current_data_single_entity_list() -> None:
    """get_preferred_choice returns entity when current_data has a single entity."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
    )
    current_data = {SECTION_COMMON: {"power": as_entity_value(["sensor.power"])}}
    result = get_preferred_choice(field, current_data, allowed_choices=ALLOWED_CHOICES_REQUIRED)
    assert result == CHOICE_ENTITY


def test_get_preferred_choice_uses_current_data_constant_value() -> None:
    """get_preferred_choice returns constant when current_data has schema constant value."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
    )
    current_data = {SECTION_COMMON: {"power": as_constant_value(25.5)}}
    result = get_preferred_choice(field, current_data, allowed_choices=ALLOWED_CHOICES_REQUIRED)
    assert result == CHOICE_CONSTANT


def test_get_preferred_choice_uses_current_data_boolean_constant() -> None:
    """get_preferred_choice returns constant when current_data has boolean constant."""
    field = InputFieldInfo(
        field_name="enabled",
        entity_description=NumberEntityDescription(
            key="enabled",
            name="Enabled",
        ),
        output_type=OutputType.STATUS,
    )
    current_data = {SECTION_COMMON: {"enabled": as_constant_value(value=True)}}
    result = get_preferred_choice(field, current_data, allowed_choices=ALLOWED_CHOICES_REQUIRED)
    assert result == CHOICE_CONSTANT


# --- Tests for get_haeo_input_entity_ids ---


def test_get_haeo_input_entity_ids_returns_empty_for_no_haeo_entities(hass: HomeAssistant) -> None:
    """get_haeo_input_entity_ids returns empty list when no HAEO input entities exist."""
    registry = er.async_get(hass)
    # Create non-HAEO entities only
    registry.async_get_or_create(
        domain="number",
        platform="other_integration",
        unique_id="external_number",
        suggested_object_id="external",
    )
    result = get_haeo_input_entity_ids()
    # Result should not include non-HAEO entities
    assert "number.external" not in result


def test_get_haeo_input_entity_ids_includes_haeo_number_and_switch(hass: HomeAssistant) -> None:
    """get_haeo_input_entity_ids includes HAEO number and switch entities."""
    registry = er.async_get(hass)
    # Create HAEO number entity
    number_entity = registry.async_get_or_create(
        domain="number",
        platform=DOMAIN,
        unique_id="test_number",
        suggested_object_id="haeo_number",
    )
    # Create HAEO switch entity
    switch_entity = registry.async_get_or_create(
        domain="switch",
        platform=DOMAIN,
        unique_id="test_switch",
        suggested_object_id="haeo_switch",
    )
    # Create non-HAEO entity
    registry.async_get_or_create(
        domain="number",
        platform="other_integration",
        unique_id="external",
        suggested_object_id="external_number",
    )
    result = get_haeo_input_entity_ids()
    assert number_entity.entity_id in result
    assert switch_entity.entity_id in result
    assert "number.external_number" not in result


def test_get_haeo_input_entity_ids_excludes_haeo_sensors(hass: HomeAssistant) -> None:
    """get_haeo_input_entity_ids excludes HAEO sensor entities."""
    registry = er.async_get(hass)
    # Create HAEO sensor (not an input entity)
    sensor_entity = registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="test_sensor",
        suggested_object_id="haeo_sensor",
    )
    result = get_haeo_input_entity_ids()
    assert sensor_entity.entity_id not in result


# --- Tests for get_choose_default ---


def test_get_choose_default_returns_none_when_no_defaults(
    hass: HomeAssistant,
) -> None:
    """get_choose_default returns None when no defaults or current_data."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
        defaults=None,
    )
    result = get_choose_default(field)
    assert result is None


def test_get_choose_default_returns_constant_for_value_mode(
    hass: HomeAssistant,
) -> None:
    """get_choose_default returns constant value for value mode defaults."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
        defaults=InputFieldDefaults(mode="value", value=10.0),
    )
    result = get_choose_default(field)
    assert result == 10.0


def test_get_choose_default_returns_empty_list_for_entity_mode(
    hass: HomeAssistant,
) -> None:
    """get_choose_default returns empty list for entity mode defaults."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
        defaults=InputFieldDefaults(mode="entity"),
    )
    result = get_choose_default(field)
    assert result == []


def test_get_choose_default_uses_current_data_constant(
    hass: HomeAssistant,
) -> None:
    """get_choose_default returns constant value from current_data."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
    )
    current_data = {SECTION_COMMON: {"power": as_constant_value(25.5)}}
    result = get_choose_default(field, current_data=current_data)
    assert result == 25.5


def test_get_choose_default_uses_current_data_entity(
    hass: HomeAssistant,
) -> None:
    """get_choose_default returns entity list from current_data."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
    )
    current_data = {SECTION_COMMON: {"power": as_entity_value(["sensor.power"])}}
    result = get_choose_default(field, current_data=current_data)
    assert result == ["sensor.power"]


def test_get_choose_default_uses_current_data_entity_list(
    hass: HomeAssistant,
) -> None:
    """get_choose_default returns entity list from current_data list."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
    )
    current_data = {SECTION_COMMON: {"power": as_entity_value(["sensor.power1", "sensor.power2"])}}
    result = get_choose_default(field, current_data=current_data)
    assert result == ["sensor.power1", "sensor.power2"]


def test_get_choose_default_uses_current_data_boolean(
    hass: HomeAssistant,
) -> None:
    """get_choose_default returns boolean value from current_data."""
    field = InputFieldInfo(
        field_name="enabled",
        entity_description=NumberEntityDescription(
            key="enabled",
            name="Enabled",
        ),
        output_type=OutputType.STATUS,
    )
    current_data = {SECTION_COMMON: {"enabled": as_constant_value(value=True)}}
    result = get_choose_default(field, current_data=current_data)
    assert result is True


def test_get_choose_default_uses_current_data_none(
    hass: HomeAssistant,
) -> None:
    """get_choose_default returns None for none values in current_data."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
    )
    current_data = {SECTION_COMMON: {"power": as_none_value()}}
    result = get_choose_default(field, current_data=current_data)
    assert result is None


def test_get_choose_default_uses_nested_current_data(
    hass: HomeAssistant,
) -> None:
    """get_choose_default searches nested current_data for the field."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
    )
    current_data = {"outer": {"inner": {"power": as_constant_value(12.0)}}}
    result = get_choose_default(field, current_data=current_data)
    assert result == 12.0


# --- Tests for convert_choose_data_to_config ---


def test_convert_choose_data_constant_stored_directly(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Constant choice value is stored as a schema value.

    After schema validation, ChooseSelector returns the raw value.
    """
    user_input: dict[str, Any] = {
        "test_field": 42.0,  # Raw value after ChooseSelector validation
    }
    result = convert_choose_data_to_config(user_input, _field_map(number_field))
    assert result["test_field"] == as_constant_value(42.0)


def test_convert_choose_data_entity_single_stored_as_string(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Single entity is stored as an entity schema value.

    After schema validation, ChooseSelector returns the entity list.
    """
    user_input: dict[str, Any] = {
        "test_field": ["sensor.power"],  # Raw list after ChooseSelector validation
    }
    result = convert_choose_data_to_config(user_input, _field_map(number_field))
    assert result["test_field"] == as_entity_value(["sensor.power"])


def test_convert_choose_data_entity_string_stored_as_list(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """String entity IDs are stored as entity schema values."""
    user_input: dict[str, Any] = {
        "test_field": "sensor.power",
    }
    result = convert_choose_data_to_config(user_input, _field_map(number_field))
    assert result["test_field"] == as_entity_value(["sensor.power"])


def test_convert_choose_data_empty_string_stored_as_none(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Empty string values are stored as none schema values."""
    user_input: dict[str, Any] = {
        "test_field": "",
    }
    result = convert_choose_data_to_config(user_input, _field_map(number_field))
    assert result["test_field"] == as_none_value()


def test_convert_choose_data_entity_multiple_stored_as_list(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Multiple entities are stored as an entity schema value.

    After schema validation, ChooseSelector returns the entity list.
    """
    user_input: dict[str, Any] = {
        "test_field": ["sensor.power1", "sensor.power2"],  # Raw list
    }
    result = convert_choose_data_to_config(user_input, _field_map(number_field))
    assert result["test_field"] == as_entity_value(["sensor.power1", "sensor.power2"])


def test_convert_choose_data_empty_value_stored_as_none(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Empty entity list is stored as none schema value."""
    user_input: dict[str, Any] = {
        "test_field": [],  # Empty list after ChooseSelector validation
    }
    result = convert_choose_data_to_config(user_input, _field_map(number_field))
    assert result["test_field"] == as_none_value()


def test_convert_choose_data_none_constant_stored_as_none(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """None value is stored as none schema value."""
    user_input: dict[str, Any] = {
        "test_field": None,
    }
    result = convert_choose_data_to_config(user_input, _field_map(number_field))
    assert result["test_field"] == as_none_value()


def test_convert_choose_data_respects_exclude_keys(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Excluded keys are not processed."""
    user_input: dict[str, Any] = {
        "name": "Test",
        "test_field": 42.0,  # Raw value
    }
    result = convert_choose_data_to_config(user_input, _field_map(number_field), exclude_keys=("name",))
    assert "name" not in result
    assert result["test_field"] == as_constant_value(42.0)


def test_convert_choose_data_ignores_unknown_fields(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Unknown fields (not in input_fields) are ignored."""
    user_input: dict[str, Any] = {
        "test_field": 42.0,  # Raw value
        "unknown_field": 99.0,  # Not in input_fields
    }
    result = convert_choose_data_to_config(user_input, _field_map(number_field))
    assert "test_field" in result
    assert "unknown_field" not in result
    assert result["test_field"] == as_constant_value(42.0)


def test_convert_choose_data_ignores_unsupported_value_types(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Unsupported value types are ignored."""
    user_input: dict[str, Any] = {
        "test_field": {"unexpected": 1},
    }
    result = convert_choose_data_to_config(user_input, _field_map(number_field))
    assert "test_field" not in result


def test_convert_choose_data_boolean_constant() -> None:
    """Boolean constant is stored correctly.

    After schema validation, ChooseSelector returns the raw boolean.
    """
    field = InputFieldInfo(
        field_name="enabled",
        entity_description=NumberEntityDescription(
            key="enabled",
            name="Enabled",
        ),
        output_type=OutputType.STATUS,
    )
    user_input: dict[str, Any] = {
        "enabled": True,  # Raw boolean
    }
    result = convert_choose_data_to_config(user_input, _field_map(field))
    assert result["enabled"] == as_constant_value(value=True)


def test_convert_choose_data_none_stored_as_none(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """None choice stores none schema value.

    After preprocessing, the none choice is converted to None.
    """
    user_input: dict[str, Any] = {
        "test_field": None,  # None from preprocessing (originally "" from ConstantSelector)
    }
    result = convert_choose_data_to_config(user_input, _field_map(number_field))
    assert result["test_field"] == as_none_value()


# --- Tests for none choice in build_choose_selector ---


def test_build_choose_selector_optional_has_none_choice(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Optional field selector includes none choice."""
    selector = build_choose_selector(number_field, allowed_choices=ALLOWED_CHOICES_OPTIONAL)
    config = selector.config
    assert CHOICE_NONE in config["choices"]
    assert CHOICE_ENTITY in config["choices"]
    assert CHOICE_CONSTANT in config["choices"]


def test_build_choose_selector_required_has_no_none_choice(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Required field selector does not include none choice."""
    selector = build_choose_selector(number_field, allowed_choices=ALLOWED_CHOICES_REQUIRED)
    config = selector.config
    assert CHOICE_NONE not in config["choices"]
    assert CHOICE_ENTITY in config["choices"]
    assert CHOICE_CONSTANT in config["choices"]


def test_build_choose_selector_none_first_when_preferred(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """None choice appears first when preferred_choice is none."""
    selector = build_choose_selector(
        number_field,
        allowed_choices=ALLOWED_CHOICES_OPTIONAL,
        preferred_choice=CHOICE_NONE,
    )
    config = selector.config
    choices_keys = list(config["choices"].keys())
    assert choices_keys[0] == CHOICE_NONE


def test_build_choose_selector_only_none_choice(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_choose_selector supports none-only allowed choices."""
    selector = build_choose_selector(number_field, allowed_choices=frozenset({CHOICE_NONE}))
    choices_keys = list(selector.config["choices"].keys())
    assert choices_keys == [CHOICE_NONE]


def test_build_choose_selector_raises_when_no_allowed_choices(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_choose_selector raises when allowed choices are empty."""
    with pytest.raises(RuntimeError, match="No allowed choices"):
        build_choose_selector(number_field, allowed_choices=frozenset())


# --- Tests for build_choose_field_entries ---


def test_build_choose_field_entries_missing_schema_metadata(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_choose_field_entries raises for missing schema metadata."""
    with pytest.raises(RuntimeError, match="Missing schema metadata"):
        build_choose_field_entries(
            _field_map(number_field),
            field_schema={},
            inclusion_map={},
        )


def test_build_choose_field_entries_none_only_value_type() -> None:
    """build_choose_field_entries supports fields with only none values."""
    field = InputFieldInfo(
        field_name="disabled",
        entity_description=NumberEntityDescription(key="disabled", name="Disabled"),
        output_type=OutputType.STATUS,
    )
    entries = build_choose_field_entries(
        {"disabled": field},
        field_schema={"disabled": FieldSchemaInfo(value_type=NoneValue, is_optional=True)},
        inclusion_map={},
    )
    marker, _selector = entries["disabled"]
    assert marker.schema == "disabled"


# --- Tests for none choice in get_preferred_choice ---


def test_get_preferred_choice_returns_none_for_optional_with_none_value() -> None:
    """get_preferred_choice returns none when current_data has none value."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
        defaults=None,
    )
    current_data = {SECTION_COMMON: {"power": as_none_value()}}
    result = get_preferred_choice(field, current_data, allowed_choices=ALLOWED_CHOICES_OPTIONAL)
    assert result == CHOICE_NONE


def test_get_preferred_choice_returns_none_for_optional_new_entry_no_defaults() -> None:
    """get_preferred_choice returns none for optional field with no defaults."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
        defaults=None,
    )
    # No current_data (new entry)
    result = get_preferred_choice(field, None, allowed_choices=ALLOWED_CHOICES_OPTIONAL)
    assert result == CHOICE_NONE


def test_get_preferred_choice_returns_value_for_optional_with_value_defaults() -> None:
    """get_preferred_choice returns constant for optional field with value defaults."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
        defaults=InputFieldDefaults(mode="value", value=10.0),
    )
    result = get_preferred_choice(field, None, allowed_choices=ALLOWED_CHOICES_OPTIONAL)
    assert result == CHOICE_CONSTANT


def test_get_preferred_choice_required_field_returns_entity_by_default() -> None:
    """get_preferred_choice for required field returns entity by default."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
        defaults=None,
    )
    # current_data exists but field is not in it
    current_data = {SECTION_COMMON: {"other_field": as_constant_value(10.0)}}
    result = get_preferred_choice(field, current_data, allowed_choices=ALLOWED_CHOICES_REQUIRED)
    # Required field should NOT return none, should return entity
    assert result == CHOICE_ENTITY


def test_get_preferred_choice_skips_unavailable_default() -> None:
    """get_preferred_choice ignores defaults when choice is unavailable."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
        defaults=InputFieldDefaults(mode="value", value=10.0),
    )
    result = get_preferred_choice(field, None, allowed_choices=frozenset({CHOICE_ENTITY}))
    assert result == CHOICE_ENTITY


def test_get_preferred_choice_constant_only_allowed() -> None:
    """get_preferred_choice returns constant when only constant is allowed."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
        defaults=None,
    )
    result = get_preferred_choice(field, None, allowed_choices=frozenset({CHOICE_CONSTANT}))
    assert result == CHOICE_CONSTANT


def test_get_preferred_choice_returns_none_for_defaults_mode_none() -> None:
    """get_preferred_choice returns none when defaults.mode is None."""
    field = InputFieldInfo(
        field_name="efficiency",
        entity_description=NumberEntityDescription(
            key="efficiency",
            name="Efficiency",
        ),
        output_type=OutputType.EFFICIENCY,
        # mode=None with a value means "default to none, but use this value if user enables"
        defaults=InputFieldDefaults(mode=None, value=100.0),
    )
    # No current_data (new entry)
    result = get_preferred_choice(field, None, allowed_choices=ALLOWED_CHOICES_OPTIONAL)
    assert result == CHOICE_NONE


def test_get_preferred_choice_defaults_mode_none_without_none_allowed() -> None:
    """get_preferred_choice falls back when none choice is unavailable."""
    field = InputFieldInfo(
        field_name="efficiency",
        entity_description=NumberEntityDescription(
            key="efficiency",
            name="Efficiency",
        ),
        output_type=OutputType.EFFICIENCY,
        defaults=InputFieldDefaults(mode=None, value=100.0),
    )
    result = get_preferred_choice(field, None, allowed_choices=frozenset({CHOICE_ENTITY}))
    assert result == CHOICE_ENTITY


def test_get_preferred_choice_returns_entity_for_defaults_mode_entity() -> None:
    """get_preferred_choice returns entity when defaults.mode is entity."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
        defaults=InputFieldDefaults(mode="entity"),
    )
    result = get_preferred_choice(field, None, allowed_choices=ALLOWED_CHOICES_OPTIONAL)
    assert result == CHOICE_ENTITY


def test_get_preferred_choice_returns_none_when_no_choices() -> None:
    """get_preferred_choice returns none when no choices are available."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
        defaults=None,
    )
    result = get_preferred_choice(field, None, allowed_choices=frozenset())
    assert result == CHOICE_NONE


# --- Tests for resolve_haeo_input_entity_id ---


def test_resolve_haeo_input_entity_id_returns_none_when_not_found(hass: HomeAssistant) -> None:
    """resolve_haeo_input_entity_id returns None when entity doesn't exist."""
    result = resolve_haeo_input_entity_id("entry123", "subentry456", "test_field")
    assert result is None


# --- Tests for build_entity_selector ---


def test_build_entity_selector_with_include_entities(hass: HomeAssistant) -> None:
    """build_entity_selector includes entities in config when provided."""
    selector = build_entity_selector(include_entities=["sensor.power", "sensor.voltage"])
    config = selector.config
    assert "include_entities" in config
    assert "sensor.power" in config["include_entities"]
    assert "sensor.voltage" in config["include_entities"]


def test_build_entity_selector_without_include_entities(hass: HomeAssistant) -> None:
    """build_entity_selector with no include_entities still includes HAEO entities."""
    selector = build_entity_selector(include_entities=None)
    config = selector.config
    # Even with None, HAEO input entities are added (if any exist)
    assert config["domain"] == [DOMAIN, "sensor", "input_number", "number", "switch"]


# --- Tests for preprocess_choose_selector_input ---


def test_preprocess_choose_selector_input_none_returns_none(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """preprocess_choose_selector_input returns None when input is None."""
    result = preprocess_choose_selector_input(None, _field_map(number_field))
    assert result is None


def test_preprocess_choose_selector_input_none_choice_returns_none(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """preprocess_choose_selector_input converts none choice to None."""
    user_input = {
        "test_field": {"active_choice": "none", "constant": 100},
    }
    result = preprocess_choose_selector_input(user_input, _field_map(number_field))
    assert result is not None
    assert result["test_field"] is None


def test_preprocess_choose_selector_input_entity_choice_extracts_entities(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """preprocess_choose_selector_input extracts entity list from entity choice."""
    user_input = {
        "test_field": {"active_choice": "entity", "entity": ["sensor.power"]},
    }
    result = preprocess_choose_selector_input(user_input, _field_map(number_field))
    assert result is not None
    assert result["test_field"] == ["sensor.power"]


def test_preprocess_choose_selector_input_constant_choice_extracts_value(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """preprocess_choose_selector_input extracts constant value from constant choice."""
    user_input = {
        "test_field": {"active_choice": "constant", "constant": 42.5},
    }
    result = preprocess_choose_selector_input(user_input, _field_map(number_field))
    assert result is not None
    assert result["test_field"] == 42.5


def test_preprocess_choose_selector_input_unknown_choice_passthrough(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """preprocess_choose_selector_input leaves unknown choices unchanged."""
    user_input = {
        "test_field": {"active_choice": "unexpected", "constant": 12.0},
    }
    result = preprocess_choose_selector_input(user_input, _field_map(number_field))
    assert result is not None
    assert result["test_field"] == {"active_choice": "unexpected", "constant": 12.0}


def test_preprocess_choose_selector_input_schema_none_value(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """preprocess_choose_selector_input converts none schema values to None."""
    user_input = {
        "test_field": as_none_value(),
    }
    result = preprocess_choose_selector_input(user_input, _field_map(number_field))
    assert result is not None
    assert result["test_field"] is None


def test_preprocess_choose_selector_input_already_normalized_passthrough(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """preprocess_choose_selector_input passes through already-normalized data."""
    # Already normalized entity list
    user_input_entity = {"test_field": ["sensor.power"]}
    result = preprocess_choose_selector_input(user_input_entity, _field_map(number_field))
    assert result is not None
    assert result["test_field"] == ["sensor.power"]

    # Already normalized constant
    user_input_constant = {"test_field": 50.0}
    result = preprocess_choose_selector_input(user_input_constant, _field_map(number_field))
    assert result is not None
    assert result["test_field"] == 50.0

    # Empty string (from ConstantSelector) is converted to None
    user_input_none = {"test_field": ""}
    result = preprocess_choose_selector_input(user_input_none, _field_map(number_field))
    assert result is not None
    assert result["test_field"] is None


def test_preprocess_choose_selector_input_ignores_non_field_keys(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """preprocess_choose_selector_input ignores keys not in input_fields."""
    user_input = {
        "test_field": {"active_choice": "none", "constant": 100},
        "name": "Test Name",  # Not in input_fields, should pass through unchanged
        "other_field": {"active_choice": "none"},  # Not in input_fields
    }
    result = preprocess_choose_selector_input(user_input, _field_map(number_field))
    assert result is not None
    assert result["test_field"] is None  # Converted to None
    assert result["name"] == "Test Name"
    # other_field is not in input_fields, so it passes through as-is
    assert result["other_field"] == {"active_choice": "none"}


def test_preprocess_choose_selector_input_entity_choice_empty_list(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """preprocess_choose_selector_input handles entity choice with missing entity key."""
    user_input = {
        "test_field": {"active_choice": "entity"},  # No entity key
    }
    result = preprocess_choose_selector_input(user_input, _field_map(number_field))
    assert result is not None
    assert result["test_field"] == []


# --- is_valid_choose_value tests ---


def test_is_valid_choose_value_with_none() -> None:
    """is_valid_choose_value returns False for None."""
    assert is_valid_choose_value(None) is False


def test_is_valid_choose_value_with_entity_list() -> None:
    """is_valid_choose_value returns True for non-empty entity lists."""
    assert is_valid_choose_value(["sensor.power"]) is True
    assert is_valid_choose_value(["sensor.a", "sensor.b"]) is True
    # Empty list is invalid
    assert is_valid_choose_value([]) is False


def test_is_valid_choose_value_with_string_entity_id() -> None:
    """is_valid_choose_value accepts string entity IDs as valid."""
    assert is_valid_choose_value("sensor.price") is True
    # Empty string is invalid
    assert is_valid_choose_value("") is False


def test_is_valid_choose_value_with_numeric_constants() -> None:
    """is_valid_choose_value returns True for numeric constants."""
    assert is_valid_choose_value(42.0) is True
    assert is_valid_choose_value(0) is True
    assert is_valid_choose_value(-10.5) is True


def test_is_valid_choose_value_with_boolean() -> None:
    """is_valid_choose_value returns True for boolean values."""
    assert is_valid_choose_value(True) is True
    assert is_valid_choose_value(False) is True


def test_is_valid_choose_value_with_unexpected_types() -> None:
    """is_valid_choose_value returns False for unexpected types."""
    assert is_valid_choose_value({"key": "value"}) is False
    assert is_valid_choose_value(object()) is False


# --- validate_choose_fields tests ---


def test_validate_choose_fields_returns_empty_for_valid_input(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """validate_choose_fields returns empty dict when all required fields are valid."""
    user_input = {"test_field": 42.0}
    field_schema = {
        "test_field": FieldSchemaInfo(value_type=EntityValue | ConstantValue, is_optional=False),
    }
    result = validate_choose_fields(user_input, _field_map(number_field), field_schema)
    assert result == {}


def test_validate_choose_fields_returns_error_for_invalid_required(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """validate_choose_fields returns error for invalid required field."""
    user_input = {"test_field": None}
    field_schema = {
        "test_field": FieldSchemaInfo(value_type=EntityValue | ConstantValue, is_optional=False),
    }
    result = validate_choose_fields(user_input, _field_map(number_field), field_schema)
    assert result == {"test_field": "required"}


def test_validate_choose_fields_skips_optional_fields(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """validate_choose_fields skips fields in optional_keys."""
    user_input = {"test_field": None}
    field_schema = {
        "test_field": FieldSchemaInfo(value_type=EntityValue | ConstantValue | NoneValue, is_optional=True),
    }
    result = validate_choose_fields(user_input, _field_map(number_field), field_schema)
    assert result == {}


def test_validate_choose_fields_skips_excluded_fields(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """validate_choose_fields skips fields in exclude_fields."""
    user_input = {"test_field": None}
    field_schema = {
        "test_field": FieldSchemaInfo(value_type=EntityValue | ConstantValue, is_optional=False),
    }
    result = validate_choose_fields(
        user_input,
        _field_map(number_field),
        field_schema,
        exclude_fields=("test_field",),
    )
    assert result == {}


def test_validate_choose_fields_raises_missing_schema_metadata(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """validate_choose_fields raises when schema metadata is missing."""
    with pytest.raises(RuntimeError, match="Missing schema metadata"):
        validate_choose_fields({"test_field": 1.0}, _field_map(number_field), {})


# --- Tests for NormalizingChooseSelector.__call__ ---


def test_normalizing_choose_selector_call_with_none_choice(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """NormalizingChooseSelector normalizes none choice dict to empty string."""
    selector = build_choose_selector(
        number_field,
        allowed_choices=ALLOWED_CHOICES_OPTIONAL,
        preferred_choice=CHOICE_NONE,
    )
    # The selector should normalize {"active_choice": "none", ...} to ""
    # and then validate it (ConstantSelector accepts "")
    result = selector({"active_choice": "none", "constant": 100})
    assert result == ""


def test_normalizing_choose_selector_call_with_entity_choice(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """NormalizingChooseSelector normalizes entity choice dict to entity list."""
    selector = build_choose_selector(
        number_field,
        allowed_choices=ALLOWED_CHOICES_REQUIRED,
        preferred_choice=CHOICE_ENTITY,
    )
    # The selector should normalize {"active_choice": "entity", "entity": [...]} to the list
    result = selector({"active_choice": "entity", "entity": ["sensor.power"]})
    assert result == ["sensor.power"]


def test_normalizing_choose_selector_call_with_constant_choice(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """NormalizingChooseSelector normalizes constant choice dict to constant value."""
    selector = build_choose_selector(
        number_field,
        allowed_choices=ALLOWED_CHOICES_REQUIRED,
        preferred_choice=CHOICE_CONSTANT,
    )
    # The selector should normalize {"active_choice": "constant", "constant": 42.0} to 42.0
    result = selector({"active_choice": "constant", "constant": 42.0})
    assert result == 42.0


def test_normalizing_choose_selector_call_passthrough_already_normalized(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """NormalizingChooseSelector passes through already-normalized values."""
    selector = build_choose_selector(
        number_field,
        allowed_choices=ALLOWED_CHOICES_REQUIRED,
        preferred_choice=CHOICE_CONSTANT,
    )
    # Already normalized constant value should pass through
    result = selector(50.0)
    assert result == 50.0


def test_normalizing_choose_selector_normalize_unknown_choice(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """NormalizingChooseSelector leaves unknown choices unchanged."""
    selector = build_choose_selector(
        number_field,
        allowed_choices=ALLOWED_CHOICES_OPTIONAL,
        preferred_choice=CHOICE_ENTITY,
    )
    raw = {"active_choice": "unexpected", "constant": 10}
    assert selector._normalize(raw) == raw


# --- Sectioned schema helpers tests ---


def test_build_section_schema_includes_sections() -> None:
    """build_section_schema includes sections with available fields."""
    sections = (
        SectionDefinition(key="common", fields=("field_a", "missing"), collapsed=True),
        SectionDefinition(key="extra", fields=("field_b",)),
        SectionDefinition(key="empty", fields=("missing_field",)),
    )
    field_entries = {
        "common": {"field_a": (vol.Required("field_a"), vol.Coerce(str))},
        "extra": {"field_b": (vol.Optional("field_b"), vol.Coerce(int))},
    }

    schema_dict = build_section_schema(sections, field_entries)

    assert {key.schema for key in schema_dict} == {"common", "extra"}


def test_build_sectioned_choose_schema_merges_extra_entries(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """build_sectioned_choose_schema merges extra entries and input fields."""
    sections = (
        SectionDefinition(key="inputs", fields=("test_field",)),
        SectionDefinition(key="extra", fields=("extra_field",)),
    )
    input_fields = {"inputs": _field_map(number_field)}
    field_schema = {
        "inputs": {"test_field": FieldSchemaInfo(value_type=EntityValue | ConstantValue, is_optional=False)}
    }
    inclusion_map = {"inputs": {"test_field": ["sensor.test"]}}
    extra_field_entries = {"extra": {"extra_field": (vol.Required("extra_field"), vol.Coerce(str))}}

    schema = build_sectioned_choose_schema(
        sections,
        input_fields,
        field_schema,
        inclusion_map,
        current_data={"inputs": {"test_field": as_entity_value(["sensor.test"])}},
        extra_field_entries=extra_field_entries,
    )

    assert {key.schema for key in schema.schema} == {"inputs", "extra"}


def test_build_sectioned_choose_defaults_merges_base_and_excludes() -> None:
    """build_sectioned_choose_defaults merges base defaults and respects exclusions."""
    field_info = InputFieldInfo(
        field_name="test_field",
        entity_description=NumberEntityDescription(key="test_field", name="Test Field"),
        output_type=OutputType.POWER,
        defaults=InputFieldDefaults(mode="value", value=10.0),
    )
    excluded_info = InputFieldInfo(
        field_name="excluded",
        entity_description=NumberEntityDescription(key="excluded", name="Excluded"),
        output_type=OutputType.POWER,
        defaults=InputFieldDefaults(mode="value", value=20.0),
    )
    sections = (SectionDefinition(key="inputs", fields=("test_field", "excluded")),)
    input_fields = {"inputs": {"test_field": field_info, "excluded": excluded_info}}

    defaults = build_sectioned_choose_defaults(
        sections,
        input_fields,
        current_data={"inputs": {"test_field": as_entity_value(["sensor.test"])}},
        base_defaults={"inputs": {"existing": "keep"}},
        exclude_fields=("excluded",),
    )

    assert defaults["inputs"]["existing"] == "keep"
    assert defaults["inputs"]["test_field"] == ["sensor.test"]
    assert "excluded" not in defaults["inputs"]


def test_preprocess_sectioned_choose_input_nests_and_normalizes(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """preprocess_sectioned_choose_input nests flat input and normalizes values."""
    sections = (SectionDefinition(key="inputs", fields=("test_field",)),)
    input_fields = {"inputs": _field_map(number_field)}

    result = preprocess_sectioned_choose_input(
        {
            "test_field": {"active_choice": CHOICE_CONSTANT, "constant": 3.0},
            "unassigned": "keep",
        },
        input_fields,
        sections,
    )

    assert result == {"inputs": {"test_field": 3.0}, "unassigned": "keep"}


def test_preprocess_sectioned_choose_input_returns_none(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """preprocess_sectioned_choose_input returns None when input is None."""
    sections = (SectionDefinition(key="inputs", fields=("test_field",)),)
    input_fields = {"inputs": _field_map(number_field)}

    assert preprocess_sectioned_choose_input(None, input_fields, sections) is None


def test_preprocess_sectioned_choose_input_skips_non_mapping_section(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """preprocess_sectioned_choose_input leaves non-mapping section input unchanged."""
    sections = (SectionDefinition(key="inputs", fields=("test_field",)),)
    input_fields = {"inputs": _field_map(number_field)}

    result = preprocess_sectioned_choose_input({"inputs": "invalid"}, input_fields, sections)

    assert result == {"inputs": "invalid"}


def test_validate_sectioned_choose_fields_skips_non_mapping_section(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """validate_sectioned_choose_fields skips non-mapping section input."""
    sections = (SectionDefinition(key="inputs", fields=("test_field",)),)
    input_fields = {"inputs": _field_map(number_field)}
    field_schema = {
        "inputs": {"test_field": FieldSchemaInfo(value_type=EntityValue | ConstantValue, is_optional=False)}
    }

    errors = validate_sectioned_choose_fields({"inputs": "invalid"}, input_fields, field_schema, sections)

    assert errors == {}


def test_convert_sectioned_choose_data_to_config_handles_non_mapping_section(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """convert_sectioned_choose_data_to_config returns empty dict for non-mapping sections."""
    sections = (SectionDefinition(key="inputs", fields=("test_field",)),)
    input_fields = {"inputs": _field_map(number_field)}

    config = convert_sectioned_choose_data_to_config({"inputs": "invalid"}, input_fields, sections)

    assert config == {"inputs": {}}
