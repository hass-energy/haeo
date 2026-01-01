"""Tests for flows/field_schema.py utilities."""

from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.helpers.selector import BooleanSelector, EntitySelector, NumberSelector
import pytest
import voluptuous as vol

from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.flows.field_schema import (
    ConfigSchemaType,
    InputMode,
    boolean_selector_from_field,
    build_mode_schema_entry,
    build_mode_selector,
    build_value_schema_entry,
    entity_selector_from_field,
    get_mode_defaults,
    get_value_defaults,
    infer_mode_from_value,
    number_selector_from_field,
)
from custom_components.haeo.model.const import OutputType

# --- Mock types ---


class MockConfigSchema(ConfigSchemaType):
    """Mock config schema for testing."""

    __optional_keys__: frozenset[str] = frozenset({"optional_field"})


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
        default=50.0,
    )


@pytest.fixture
def switch_field() -> InputFieldInfo[SwitchEntityDescription]:
    """Create a switch input field for testing."""
    return InputFieldInfo(
        field_name="test_switch",
        entity_description=SwitchEntityDescription(
            key="test_switch",
            name="Test Switch",
        ),
        output_type=OutputType.STATUS,
        default=True,
    )


@pytest.fixture
def required_field() -> InputFieldInfo[NumberEntityDescription]:
    """Create a required input field (no default) for testing."""
    return InputFieldInfo(
        field_name="required_field",
        entity_description=NumberEntityDescription(
            key="required_field",
            name="Required Field",
            native_min_value=0.0,
            native_max_value=100.0,
        ),
        output_type=OutputType.POWER,
        default=None,
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


# --- Tests for entity_selector_from_field ---


def test_entity_selector_from_field_creates_selector(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Entity selector is created."""
    selector = entity_selector_from_field(number_field)
    assert isinstance(selector, EntitySelector)


def test_entity_selector_from_field_with_exclusions(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Entity selector excludes specified entities."""
    selector = entity_selector_from_field(number_field, exclude_entities=["sensor.excluded"])
    assert isinstance(selector, EntitySelector)


# --- Tests for infer_mode_from_value ---


def test_infer_mode_from_value_none_returns_none_mode() -> None:
    """None value infers NONE mode."""
    assert infer_mode_from_value(None) == InputMode.NONE


def test_infer_mode_from_value_empty_list_returns_none_mode() -> None:
    """Empty list infers NONE mode."""
    assert infer_mode_from_value([]) == InputMode.NONE


def test_infer_mode_from_value_entity_list_returns_entity_link_mode() -> None:
    """List of entity IDs infers ENTITY_LINK mode."""
    assert infer_mode_from_value(["sensor.test"]) == InputMode.ENTITY_LINK


def test_infer_mode_from_value_float_returns_constant_mode() -> None:
    """Float value infers CONSTANT mode."""
    assert infer_mode_from_value(3.14) == InputMode.CONSTANT


def test_infer_mode_from_value_int_returns_constant_mode() -> None:
    """Int value infers CONSTANT mode."""
    assert infer_mode_from_value(42) == InputMode.CONSTANT


def test_infer_mode_from_value_bool_returns_constant_mode() -> None:
    """Bool value infers CONSTANT mode."""
    assert infer_mode_from_value(True) == InputMode.CONSTANT
    assert infer_mode_from_value(False) == InputMode.CONSTANT


def test_infer_mode_from_value_unknown_type_returns_none_mode() -> None:
    """Unknown type returns NONE mode."""
    assert infer_mode_from_value({"unknown": "dict"}) == InputMode.NONE


# --- Tests for build_mode_selector ---


def test_build_mode_selector_with_default_includes_none_option() -> None:
    """Mode selector with default includes NONE option."""
    selector = build_mode_selector(has_default=True)
    assert selector is not None


def test_build_mode_selector_without_default_excludes_none_option() -> None:
    """Mode selector without default excludes NONE option."""
    selector = build_mode_selector(has_default=False)
    assert selector is not None


# --- Tests for build_mode_schema_entry ---


def test_build_mode_schema_entry_optional_field_has_default(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Optional field creates Required schema entry with default of NONE."""
    schema = MockConfigSchema()
    schema.__optional_keys__ = frozenset({"test_field"})

    marker, _selector = build_mode_schema_entry(number_field, config_schema=schema)

    assert isinstance(marker, vol.Required)
    assert marker.schema == "test_field_mode"
    assert callable(marker.default)
    assert marker.default() == InputMode.NONE


def test_build_mode_schema_entry_required_field_no_default(
    required_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Required field creates Required schema entry without default."""
    schema = MockConfigSchema()
    schema.__optional_keys__ = frozenset()

    marker, _selector = build_mode_schema_entry(required_field, config_schema=schema)

    assert isinstance(marker, vol.Required)
    assert marker.schema == "required_field_mode"
    assert marker.default is vol.UNDEFINED


# --- Tests for build_value_schema_entry ---


def test_build_value_schema_entry_none_mode_returns_none(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """NONE mode returns None schema entry."""
    result = build_value_schema_entry(number_field, mode=InputMode.NONE)
    assert result is None


def test_build_value_schema_entry_constant_mode_number_field(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """CONSTANT mode for number field creates number selector."""
    result = build_value_schema_entry(number_field, mode=InputMode.CONSTANT)
    assert result is not None
    marker, selector = result
    assert isinstance(marker, vol.Optional)
    assert isinstance(selector, NumberSelector)


def test_build_value_schema_entry_constant_mode_switch_field(
    switch_field: InputFieldInfo[SwitchEntityDescription],
) -> None:
    """CONSTANT mode for switch field creates boolean selector."""
    result = build_value_schema_entry(switch_field, mode=InputMode.CONSTANT)
    assert result is not None
    marker, selector = result
    assert isinstance(marker, vol.Optional)
    assert isinstance(selector, BooleanSelector)


def test_build_value_schema_entry_constant_mode_required_field(
    required_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """CONSTANT mode for required field creates Required marker."""
    result = build_value_schema_entry(required_field, mode=InputMode.CONSTANT)
    assert result is not None
    marker, _selector = result
    assert isinstance(marker, vol.Required)


def test_build_value_schema_entry_entity_link_mode(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """ENTITY_LINK mode creates entity selector."""
    result = build_value_schema_entry(number_field, mode=InputMode.ENTITY_LINK)
    assert result is not None
    marker, _selector = result
    assert isinstance(marker, vol.Optional)


def test_build_value_schema_entry_entity_link_mode_required(
    required_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """ENTITY_LINK mode for required field creates Required marker."""
    result = build_value_schema_entry(required_field, mode=InputMode.ENTITY_LINK)
    assert result is not None
    marker, _selector = result
    assert isinstance(marker, vol.Required)


def test_build_value_schema_entry_entity_link_with_exclusions(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """ENTITY_LINK mode respects exclude_entities."""
    result = build_value_schema_entry(number_field, mode=InputMode.ENTITY_LINK, exclude_entities=["sensor.excluded"])
    assert result is not None


# --- Tests for get_mode_defaults ---


def test_get_mode_defaults_new_entry_optional_field(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """New entry optional field defaults to NONE."""
    schema = MockConfigSchema()
    schema.__optional_keys__ = frozenset({"test_field"})

    defaults = get_mode_defaults((number_field,), schema)

    assert defaults["test_field_mode"] == InputMode.NONE


def test_get_mode_defaults_new_entry_required_field(
    required_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """New entry required field defaults to CONSTANT."""
    schema = MockConfigSchema()
    schema.__optional_keys__ = frozenset()

    defaults = get_mode_defaults((required_field,), schema)

    assert defaults["required_field_mode"] == InputMode.CONSTANT


def test_get_mode_defaults_reconfigure_preserves_mode(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Reconfigure preserves existing mode."""
    schema = MockConfigSchema()
    current_data = {"test_field": ["sensor.test"]}

    defaults = get_mode_defaults((number_field,), schema, current_data)

    assert defaults["test_field_mode"] == InputMode.ENTITY_LINK


# --- Tests for get_value_defaults ---


def test_get_value_defaults_new_entry_uses_default(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """New entry uses field default for constant mode."""
    modes: dict[str, str] = {"test_field_mode": InputMode.CONSTANT}

    defaults = get_value_defaults((number_field,), modes)

    assert defaults["test_field"] == 50.0


def test_get_value_defaults_reconfigure_preserves_value(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Reconfigure preserves current value when mode matches."""
    modes: dict[str, str] = {"test_field_mode": InputMode.CONSTANT}
    current_data = {"test_field": 75.0}

    defaults = get_value_defaults((number_field,), modes, current_data)

    assert defaults["test_field"] == 75.0


def test_get_value_defaults_mode_change_uses_default(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """Mode change from ENTITY_LINK to CONSTANT uses default."""
    modes: dict[str, str] = {"test_field_mode": InputMode.CONSTANT}
    current_data = {"test_field": ["sensor.test"]}

    defaults = get_value_defaults((number_field,), modes, current_data)

    assert defaults["test_field"] == 50.0


def test_get_value_defaults_none_mode_excluded(
    number_field: InputFieldInfo[NumberEntityDescription],
) -> None:
    """NONE mode fields are not included in defaults."""
    modes: dict[str, str] = {"test_field_mode": InputMode.NONE}

    defaults = get_value_defaults((number_field,), modes)

    assert "test_field" not in defaults
