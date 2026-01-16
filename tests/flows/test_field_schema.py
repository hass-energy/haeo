"""Tests for flows/field_schema.py utilities."""

from typing import Any

from homeassistant.components.number import NumberEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import BooleanSelector, NumberSelector
import pytest

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.elements.input_fields import InputFieldDefaults, InputFieldInfo
from custom_components.haeo.flows.field_schema import (
    CHOICE_CONSTANT,
    CHOICE_ENTITY,
    CHOICE_NONE,
    NormalizingChooseSelector,
    _normalize_entity_selection,
    boolean_selector_from_field,
    build_choose_selector,
    build_entity_selector,
    convert_choose_data_to_config,
    get_choose_default,
    get_haeo_input_entity_ids,
    get_preferred_choice,
    is_valid_choose_value,
    number_selector_from_field,
    preprocess_choose_selector_input,
    resolve_haeo_input_entity_id,
    validate_choose_fields,
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


# --- Tests for build_choose_selector ---


def test_build_choose_selector_creates_normalizing_choose_selector(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """NormalizingChooseSelector is created with entity and constant choices."""
    selector = build_choose_selector(number_field)
    assert isinstance(selector, NormalizingChooseSelector)


def test_build_choose_selector_entity_first_by_default(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Entity choice appears first when preferred_choice is entity."""
    selector = build_choose_selector(number_field, preferred_choice=CHOICE_ENTITY)
    config = selector.config
    choices_keys = list(config["choices"].keys())
    assert choices_keys[0] == CHOICE_ENTITY
    assert choices_keys[1] == CHOICE_CONSTANT


def test_build_choose_selector_constant_first_when_preferred(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Constant choice appears first when preferred_choice is constant."""
    selector = build_choose_selector(number_field, preferred_choice=CHOICE_CONSTANT)
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
    result = get_preferred_choice(field)
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
    result = get_preferred_choice(field)
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
    result = get_preferred_choice(field)
    assert result == CHOICE_ENTITY


def test_get_preferred_choice_uses_current_data_string_as_entity() -> None:
    """get_preferred_choice returns entity when current_data has string value."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
    )
    current_data = {"power": "sensor.power"}
    result = get_preferred_choice(field, current_data)
    assert result == CHOICE_ENTITY


def test_get_preferred_choice_uses_current_data_list_as_entity() -> None:
    """get_preferred_choice returns entity when current_data has list value.

    This covers the case where multiple=True is used on EntitySelector,
    which stores entity IDs as a list (e.g., for chained sensors).
    """
    field = InputFieldInfo(
        field_name="import_price",
        entity_description=NumberEntityDescription(
            key="import_price",
            name="Import Price",
        ),
        output_type=OutputType.PRICE,
    )
    current_data = {"import_price": ["sensor.current_price", "sensor.forecast_price"]}
    result = get_preferred_choice(field, current_data)
    assert result == CHOICE_ENTITY


def test_get_preferred_choice_uses_current_data_single_item_list_as_entity() -> None:
    """get_preferred_choice returns entity when current_data has single-item list.

    Even a single entity stored as a list should be recognized as entity mode.
    """
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
    )
    current_data = {"power": ["sensor.power"]}
    result = get_preferred_choice(field, current_data)
    assert result == CHOICE_ENTITY


def test_get_preferred_choice_uses_current_data_number_as_constant() -> None:
    """get_preferred_choice returns constant when current_data has number value."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
    )
    current_data = {"power": 25.5}
    result = get_preferred_choice(field, current_data)
    assert result == CHOICE_CONSTANT


def test_get_preferred_choice_uses_current_data_boolean_as_constant() -> None:
    """get_preferred_choice returns constant when current_data has boolean value."""
    field = InputFieldInfo(
        field_name="enabled",
        entity_description=NumberEntityDescription(
            key="enabled",
            name="Enabled",
        ),
        output_type=OutputType.STATUS,
    )
    current_data = {"enabled": True}
    result = get_preferred_choice(field, current_data)
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
    current_data = {"power": 25.5}
    result = get_choose_default(field, current_data=current_data)
    assert result == 25.5


def test_get_choose_default_uses_current_data_entity(
    hass: HomeAssistant,
) -> None:
    """get_choose_default returns entity list from current_data string."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
    )
    current_data = {"power": "sensor.power"}
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
    current_data = {"power": ["sensor.power1", "sensor.power2"]}
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
    current_data = {"enabled": True}
    result = get_choose_default(field, current_data=current_data)
    assert result is True


# --- Tests for convert_choose_data_to_config ---


def test_convert_choose_data_constant_stored_directly(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Constant choice value is stored directly.

    After schema validation, ChooseSelector returns the raw value.
    """
    user_input: dict[str, Any] = {
        "test_field": 42.0,  # Raw value after ChooseSelector validation
    }
    result = convert_choose_data_to_config(user_input, (number_field,))
    assert result["test_field"] == 42.0


def test_convert_choose_data_entity_single_stored_as_string(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Single entity is stored as string.

    After schema validation, ChooseSelector returns the entity list.
    """
    user_input: dict[str, Any] = {
        "test_field": ["sensor.power"],  # Raw list after ChooseSelector validation
    }
    result = convert_choose_data_to_config(user_input, (number_field,))
    assert result["test_field"] == "sensor.power"


def test_convert_choose_data_entity_multiple_stored_as_list(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Multiple entities are stored as list.

    After schema validation, ChooseSelector returns the entity list.
    """
    user_input: dict[str, Any] = {
        "test_field": ["sensor.power1", "sensor.power2"],  # Raw list
    }
    result = convert_choose_data_to_config(user_input, (number_field,))
    assert result["test_field"] == ["sensor.power1", "sensor.power2"]


def test_convert_choose_data_empty_value_omitted(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Empty entity list is omitted from config."""
    user_input: dict[str, Any] = {
        "test_field": [],  # Empty list after ChooseSelector validation
    }
    result = convert_choose_data_to_config(user_input, (number_field,))
    assert "test_field" not in result


def test_convert_choose_data_none_constant_omitted(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """None value is omitted from config."""
    user_input: dict[str, Any] = {
        "test_field": None,
    }
    result = convert_choose_data_to_config(user_input, (number_field,))
    assert "test_field" not in result


def test_convert_choose_data_respects_exclude_keys(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Excluded keys are not processed."""
    user_input: dict[str, Any] = {
        "name": "Test",
        "test_field": 42.0,  # Raw value
    }
    result = convert_choose_data_to_config(user_input, (number_field,), exclude_keys=("name",))
    assert "name" not in result
    assert result["test_field"] == 42.0


def test_convert_choose_data_ignores_unknown_fields(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Unknown fields (not in input_fields) are ignored."""
    user_input: dict[str, Any] = {
        "test_field": 42.0,  # Raw value
        "unknown_field": 99.0,  # Not in input_fields
    }
    result = convert_choose_data_to_config(user_input, (number_field,))
    assert "test_field" in result
    assert "unknown_field" not in result


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
    result = convert_choose_data_to_config(user_input, (field,))
    assert result["enabled"] is True


def test_convert_choose_data_none_omits_field(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """None choice omits field from config.

    After preprocessing, the none choice is converted to None.
    """
    user_input: dict[str, Any] = {
        "test_field": None,  # None from preprocessing (originally "" from ConstantSelector)
    }
    result = convert_choose_data_to_config(user_input, (number_field,))
    assert "test_field" not in result


# --- Tests for none choice in build_choose_selector ---


def test_build_choose_selector_optional_has_none_choice(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Optional field selector includes none choice."""
    selector = build_choose_selector(number_field, is_optional=True)
    config = selector.config
    assert CHOICE_NONE in config["choices"]
    assert CHOICE_ENTITY in config["choices"]
    assert CHOICE_CONSTANT in config["choices"]


def test_build_choose_selector_required_has_no_none_choice(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Required field selector does not include none choice."""
    selector = build_choose_selector(number_field, is_optional=False)
    config = selector.config
    assert CHOICE_NONE not in config["choices"]
    assert CHOICE_ENTITY in config["choices"]
    assert CHOICE_CONSTANT in config["choices"]


def test_build_choose_selector_none_first_when_preferred(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """None choice appears first when preferred_choice is none."""
    selector = build_choose_selector(number_field, is_optional=True, preferred_choice=CHOICE_NONE)
    config = selector.config
    choices_keys = list(config["choices"].keys())
    assert choices_keys[0] == CHOICE_NONE


# --- Tests for none choice in get_preferred_choice ---


def test_get_preferred_choice_returns_none_for_optional_without_data() -> None:
    """get_preferred_choice returns none for optional field not in current_data."""
    field = InputFieldInfo(
        field_name="power",
        entity_description=NumberEntityDescription(
            key="power",
            name="Power",
        ),
        output_type=OutputType.POWER,
        defaults=None,
    )
    # current_data exists but field is not in it (meaning it was set to none)
    current_data = {"other_field": 10.0}
    result = get_preferred_choice(field, current_data, is_optional=True)
    assert result == CHOICE_NONE


def test_get_preferred_choice_returns_none_for_optional_new_entry_no_defaults() -> None:
    """get_preferred_choice returns none for optional field with no defaults in new entry."""
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
    result = get_preferred_choice(field, None, is_optional=True)
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
    result = get_preferred_choice(field, None, is_optional=True)
    assert result == CHOICE_CONSTANT


def test_get_preferred_choice_required_field_ignores_is_optional_false() -> None:
    """get_preferred_choice for required field (is_optional=False) returns entity by default."""
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
    current_data = {"other_field": 10.0}
    result = get_preferred_choice(field, current_data, is_optional=False)
    # Required field should NOT return none, should return entity
    assert result == CHOICE_ENTITY


def test_get_preferred_choice_returns_none_for_defaults_mode_none() -> None:
    """get_preferred_choice returns none when defaults.mode is None for optional field."""
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
    result = get_preferred_choice(field, None, is_optional=True)
    assert result == CHOICE_NONE


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
    result = get_preferred_choice(field, None, is_optional=True)
    assert result == CHOICE_ENTITY


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


# --- Tests for _normalize_entity_selection ---


def test_normalize_entity_selection_with_string_returns_string() -> None:
    """_normalize_entity_selection returns string unchanged when passed a string."""
    result = _normalize_entity_selection("sensor.power")
    assert result == "sensor.power"


def test_normalize_entity_selection_single_element_list_returns_string() -> None:
    """_normalize_entity_selection extracts single element from list."""
    result = _normalize_entity_selection(["sensor.power"])
    assert result == "sensor.power"


def test_normalize_entity_selection_multi_element_list_returns_list() -> None:
    """_normalize_entity_selection keeps multi-element list as list."""
    result = _normalize_entity_selection(["sensor.power1", "sensor.power2"])
    assert result == ["sensor.power1", "sensor.power2"]


# --- Tests for preprocess_choose_selector_input ---


def test_preprocess_choose_selector_input_none_returns_none(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """preprocess_choose_selector_input returns None when input is None."""
    result = preprocess_choose_selector_input(None, (number_field,))
    assert result is None


def test_preprocess_choose_selector_input_none_choice_returns_none(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """preprocess_choose_selector_input converts none choice to None."""
    user_input = {
        "test_field": {"active_choice": "none", "constant": 100},
    }
    result = preprocess_choose_selector_input(user_input, (number_field,))
    assert result is not None
    assert result["test_field"] is None


def test_preprocess_choose_selector_input_entity_choice_extracts_entities(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """preprocess_choose_selector_input extracts entity list from entity choice."""
    user_input = {
        "test_field": {"active_choice": "entity", "entity": ["sensor.power"]},
    }
    result = preprocess_choose_selector_input(user_input, (number_field,))
    assert result is not None
    assert result["test_field"] == ["sensor.power"]


def test_preprocess_choose_selector_input_constant_choice_extracts_value(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """preprocess_choose_selector_input extracts constant value from constant choice."""
    user_input = {
        "test_field": {"active_choice": "constant", "constant": 42.5},
    }
    result = preprocess_choose_selector_input(user_input, (number_field,))
    assert result is not None
    assert result["test_field"] == 42.5


def test_preprocess_choose_selector_input_already_normalized_passthrough(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """preprocess_choose_selector_input passes through already-normalized data."""
    # Already normalized entity list
    user_input_entity = {"test_field": ["sensor.power"]}
    result = preprocess_choose_selector_input(user_input_entity, (number_field,))
    assert result is not None
    assert result["test_field"] == ["sensor.power"]

    # Already normalized constant
    user_input_constant = {"test_field": 50.0}
    result = preprocess_choose_selector_input(user_input_constant, (number_field,))
    assert result is not None
    assert result["test_field"] == 50.0

    # Empty string (from ConstantSelector) is converted to None
    user_input_none = {"test_field": ""}
    result = preprocess_choose_selector_input(user_input_none, (number_field,))
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
    result = preprocess_choose_selector_input(user_input, (number_field,))
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
    result = preprocess_choose_selector_input(user_input, (number_field,))
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
    result = validate_choose_fields(user_input, (number_field,), frozenset())
    assert result == {}


def test_validate_choose_fields_returns_error_for_invalid_required(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """validate_choose_fields returns error for invalid required field."""
    user_input = {"test_field": None}
    result = validate_choose_fields(user_input, (number_field,), frozenset())
    assert result == {"test_field": "required"}


def test_validate_choose_fields_skips_optional_fields(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """validate_choose_fields skips fields in optional_keys."""
    user_input = {"test_field": None}
    # Mark test_field as optional
    result = validate_choose_fields(user_input, (number_field,), frozenset({"test_field"}))
    assert result == {}


def test_validate_choose_fields_skips_excluded_fields(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """validate_choose_fields skips fields in exclude_fields."""
    user_input = {"test_field": None}
    result = validate_choose_fields(user_input, (number_field,), frozenset(), exclude_fields=("test_field",))
    assert result == {}


# --- Tests for NormalizingChooseSelector.__call__ ---


def test_normalizing_choose_selector_call_with_none_choice(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """NormalizingChooseSelector normalizes none choice dict to empty string."""
    selector = build_choose_selector(number_field, is_optional=True, preferred_choice=CHOICE_NONE)
    # The selector should normalize {"active_choice": "none", ...} to ""
    # and then validate it (ConstantSelector accepts "")
    result = selector({"active_choice": "none", "constant": 100})
    assert result == ""


def test_normalizing_choose_selector_call_with_entity_choice(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """NormalizingChooseSelector normalizes entity choice dict to entity list."""
    selector = build_choose_selector(number_field, preferred_choice=CHOICE_ENTITY)
    # The selector should normalize {"active_choice": "entity", "entity": [...]} to the list
    result = selector({"active_choice": "entity", "entity": ["sensor.power"]})
    assert result == ["sensor.power"]


def test_normalizing_choose_selector_call_with_constant_choice(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """NormalizingChooseSelector normalizes constant choice dict to constant value."""
    selector = build_choose_selector(number_field, preferred_choice=CHOICE_CONSTANT)
    # The selector should normalize {"active_choice": "constant", "constant": 42.0} to 42.0
    result = selector({"active_choice": "constant", "constant": 42.0})
    assert result == 42.0


def test_normalizing_choose_selector_call_passthrough_already_normalized(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """NormalizingChooseSelector passes through already-normalized values."""
    selector = build_choose_selector(number_field, preferred_choice=CHOICE_CONSTANT)
    # Already normalized constant value should pass through
    result = selector(50.0)
    assert result == 50.0
