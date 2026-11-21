"""Tests for flows/field_schema.py utilities."""

from dataclasses import replace

from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
import pytest
import voluptuous as vol

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import (
    ConstantValue,
    EntityValue,
    NoneValue,
    SchemaValue,
    as_constant_value,
    as_entity_value,
    as_none_value,
)
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.field_hints import CalendarFieldHint
from custom_components.haeo.elements import get_input_fields
from custom_components.haeo.elements.input_fields import (
    AnyInputFieldInfo,
    FieldSchemaInfo,
    InputFieldDefaults,
    InputFieldInfo,
    is_switch_field_info,
)
from custom_components.haeo.flows.field_schema import (
    SectionDefinition,
    build_input_field_entries,
    build_input_selector,
    build_section_schema,
    build_sectioned_input_defaults,
    build_sectioned_input_schema,
    convert_sectioned_input_to_config,
    entity_domains,
    get_input_default,
    has_input_value,
    input_kinds,
    validate_input_fields,
    validate_sectioned_input_fields,
)
from custom_components.haeo.flows.input_selector import InputKind, InputSelector

BASE_DOMAINS = ["haeo", "sensor", "input_number", "number", "switch"]

REQUIRED = FieldSchemaInfo(value_type=EntityValue | ConstantValue, is_optional=False)
OPTIONAL = FieldSchemaInfo(value_type=EntityValue | ConstantValue | NoneValue, is_optional=True)

POWER = InputFieldInfo(
    field_name="power",
    entity_description=NumberEntityDescription(
        key="power",
        native_min_value=0.0,
        native_max_value=100.0,
        native_step=0.5,
        native_unit_of_measurement="kW",
    ),
    output_type=OutputType.POWER,
    defaults=InputFieldDefaults(mode="value", value=50.0),
)
PRICE = InputFieldInfo(
    field_name="price",
    entity_description=NumberEntityDescription(key="price"),
    output_type=OutputType.PRICE,
)
ENABLED = InputFieldInfo(
    field_name="enabled",
    entity_description=SwitchEntityDescription(key="enabled"),
    output_type=OutputType.STATUS,
    defaults=InputFieldDefaults(mode="value", value=True),
)

SECTIONS = (
    SectionDefinition(key="limits", fields=("power", "price")),
    SectionDefinition(key="options", fields=("enabled", "label"), collapsed=True),
)
INPUT_FIELDS = {"limits": {"power": POWER, "price": PRICE}, "options": {"enabled": ENABLED}}
FIELD_SCHEMA = {"limits": {"power": REQUIRED, "price": OPTIONAL}, "options": {"enabled": OPTIONAL}}


def _calendar_field() -> InputFieldInfo[NumberEntityDescription]:
    """Create a config field feeding a calendar input."""
    output = InputFieldInfo(
        field_name="window_due",
        entity_description=NumberEntityDescription(key="window_due"),
        output_type=OutputType.ENERGY,
        time_series=True,
        boundaries=True,
        calendar=CalendarFieldHint(projection="event_due"),
        source_field="window_calendar",
    )
    return InputFieldInfo(
        field_name="window_calendar",
        entity_description=NumberEntityDescription(key="window_calendar"),
        output_type=OutputType.ENERGY,
        outputs={"window_due": output},
    )


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        pytest.param(POWER, BASE_DOMAINS, id="scalar"),
        pytest.param(replace(POWER, time_series=True), [*BASE_DOMAINS, "calendar"], id="forecast_with_unit"),
        pytest.param(
            replace(POWER, time_series=True, output_type=OutputType.AVAILABILITY),
            [*BASE_DOMAINS, "binary_sensor", "input_boolean"],
            id="on_off_forecast",
        ),
        pytest.param(ENABLED, [*BASE_DOMAINS, "binary_sensor", "input_boolean"], id="on_off"),
        pytest.param(_calendar_field(), ["calendar"], id="calendar_field"),
    ],
)
def test_entity_domains(field: AnyInputFieldInfo, expected: list[str]) -> None:
    """A field offers the input domains, plus calendars for unit forecasts and on/off entities for on/off fields."""
    assert entity_domains(field) == expected


def test_switch_inputs_offer_on_off_entities() -> None:
    """Every switch input can read binary sensors and input booleans as well as numeric entities."""
    switches = [
        info
        for element_type in (ElementType.EV, ElementType.SOLAR)
        for section in get_input_fields(element_type).values()
        for info in section.values()
        if is_switch_field_info(info)
    ]

    assert switches
    for info in switches:
        assert {"binary_sensor", "input_boolean"} <= set(entity_domains(info))


@pytest.mark.parametrize(
    ("value_type", "force_required", "expected"),
    [
        pytest.param(EntityValue | ConstantValue, None, ["entity", "constant"], id="required"),
        pytest.param(EntityValue | ConstantValue | NoneValue, None, ["entity", "constant", "none"], id="optional"),
        pytest.param(EntityValue | ConstantValue | NoneValue, True, ["entity", "constant"], id="force_required"),
        pytest.param(EntityValue, None, ["entity"], id="entity_only"),
        pytest.param(ConstantValue | NoneValue, None, ["constant", "none"], id="constant_or_none"),
    ],
)
def test_input_kinds(value_type: object, force_required: bool | None, expected: list[InputKind]) -> None:
    """A field offers the kinds its schema type holds, in a fixed order, without none when forced required."""
    field = replace(POWER, force_required=force_required)

    assert input_kinds(FieldSchemaInfo(value_type=value_type, is_optional=True), field) == expected


def test_build_input_selector_takes_number_limits_from_the_entity_description() -> None:
    """A number field's constant takes the limits, step and unit of its number entity."""
    selector = build_input_selector(POWER, kinds=["entity", "constant"], entities=["sensor.power"])

    assert selector.config == {
        "kinds": ["entity", "constant"],
        "value_type": "number",
        "multiple": True,
        "entities": ["sensor.power"],
        "min": 0.0,
        "max": 100.0,
        "step": 0.5,
        "unit": "kW",
    }


@pytest.mark.parametrize(
    ("field", "value_type"),
    [pytest.param(PRICE, "number", id="number_without_limits"), pytest.param(ENABLED, "boolean", id="switch")],
)
def test_build_input_selector_without_limits(field: AnyInputFieldInfo, value_type: str) -> None:
    """A field whose entity states no limits, or a switch field, offers an unbounded constant."""
    selector = build_input_selector(field, kinds=["constant"], entities=[], multiple=False)

    assert selector.config == {"kinds": ["constant"], "value_type": value_type, "multiple": False, "entities": []}


@pytest.mark.parametrize(
    ("schema_info", "force_required", "marker"),
    [
        pytest.param(REQUIRED, None, vol.Required, id="required"),
        pytest.param(OPTIONAL, None, vol.Optional, id="optional"),
        pytest.param(OPTIONAL, True, vol.Required, id="force_required"),
    ],
)
def test_build_input_field_entries_markers(
    schema_info: FieldSchemaInfo, force_required: bool | None, marker: type[vol.Marker]
) -> None:
    """An input may be left out of a submission only when the field is optional and not forced required."""
    field = replace(POWER, force_required=force_required)

    entries = build_input_field_entries(
        {"power": field}, field_schema={"power": schema_info}, inclusion_map={"power": ["sensor.power"]}
    )

    key, selector = entries["power"]
    assert type(key) is marker
    assert key.schema == "power"
    assert selector == build_input_selector(field, kinds=input_kinds(schema_info, field), entities=["sensor.power"])


def test_build_input_field_entries_requires_schema_metadata() -> None:
    """A field the element's schema does not describe is a coding error."""
    with pytest.raises(RuntimeError, match="Missing schema metadata"):
        build_input_field_entries({"power": POWER}, field_schema={}, inclusion_map={"power": []})


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


def test_build_sectioned_input_schema_validates_submissions() -> None:
    """The sectioned schema places top-level and extra entries, and validates each input into its stored form."""
    schema = build_sectioned_input_schema(
        SECTIONS,
        INPUT_FIELDS,
        FIELD_SCHEMA,
        {"limits": {"power": ["sensor.power"], "price": []}, "options": {"enabled": []}},
        extra_field_entries={"options": {"label": (vol.Optional("label"), str)}},
        top_level_entries={"name": (vol.Required("name"), str)},
    )

    assert [str(key) for key in schema.schema] == ["name", "limits", "options"]
    assert schema(
        {
            "name": "Battery",
            "limits": {
                "power": {"type": "entity", "value": ["sensor.power"]},
                "price": {"type": "entity", "value": []},
            },
            "options": {"enabled": {"type": "constant", "value": "on"}, "label": "Main"},
        }
    ) == {
        "name": "Battery",
        "limits": {"power": as_entity_value(["sensor.power"]), "price": as_none_value()},
        "options": {"enabled": as_constant_value(True), "label": "Main"},
    }
    with pytest.raises(vol.Invalid):
        schema({"name": "Battery", "limits": {"price": as_none_value()}, "options": {}})


@pytest.mark.parametrize(
    ("field", "current_data", "expected"),
    [
        pytest.param(
            POWER, {"power": as_entity_value(["sensor.a"])}, as_entity_value(["sensor.a"]), id="stored_entity"
        ),
        pytest.param(POWER, {"power": as_constant_value(5.0)}, as_constant_value(5.0), id="stored_constant"),
        pytest.param(ENABLED, {"enabled": as_constant_value(False)}, as_constant_value(False), id="stored_boolean"),
        pytest.param(POWER, {"power": as_none_value()}, as_none_value(), id="stored_none"),
        pytest.param(POWER, {"limits": {"power": as_constant_value(5.0)}}, as_constant_value(5.0), id="nested"),
        pytest.param(POWER, {"power": 5.0}, as_constant_value(50.0), id="stored_non_schema_value"),
        pytest.param(POWER, None, as_constant_value(50.0), id="value_default"),
        pytest.param(ENABLED, {}, as_constant_value(True), id="boolean_default"),
        pytest.param(
            replace(POWER, defaults=InputFieldDefaults(mode="entity", entity="sensor.a")),
            None,
            as_none_value(),
            id="entity_default",
        ),
        pytest.param(PRICE, None, as_none_value(), id="no_default"),
    ],
)
def test_get_input_default(
    field: AnyInputFieldInfo, current_data: dict[str, object] | None, expected: SchemaValue
) -> None:
    """A field opens with its stored value, else a constant for a value default, else no value."""
    assert get_input_default(field, current_data) == expected


def test_build_sectioned_input_defaults() -> None:
    """Every input opens with a value; base defaults win, and excluded fields are left out."""
    defaults = build_sectioned_input_defaults(
        SECTIONS,
        INPUT_FIELDS,
        current_data={"limits": {"power": as_entity_value(["sensor.a"])}, "options": "invalid"},
        base_defaults={"limits": {"existing": "keep"}, "options": {"enabled": as_constant_value(False)}},
        exclude_fields=("price",),
    )

    assert defaults == {
        "limits": {"existing": "keep", "power": as_entity_value(["sensor.a"])},
        "options": {"enabled": as_constant_value(False)},
    }


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(as_entity_value(["sensor.a"]), True, id="entity"),
        pytest.param(as_constant_value(0.0), True, id="zero"),
        pytest.param(as_constant_value(False), True, id="false"),
        pytest.param(as_none_value(), False, id="none"),
        pytest.param(None, False, id="missing"),
        pytest.param(5.0, False, id="not_a_schema_value"),
    ],
)
def test_has_input_value(value: object, expected: bool) -> None:
    """An input holds a value when it is a schema value other than none."""
    assert has_input_value(value) is expected


@pytest.mark.parametrize(
    ("user_input", "exclude_fields", "expected"),
    [
        pytest.param({"power": as_constant_value(1.0), "price": as_none_value()}, (), {}, id="valid"),
        pytest.param({"price": as_constant_value(1.0)}, (), {"power": "required"}, id="required_missing"),
        pytest.param({"power": as_none_value()}, (), {"power": "required"}, id="required_none"),
        pytest.param({"power": as_none_value()}, ("power",), {}, id="excluded"),
    ],
)
def test_validate_input_fields(
    user_input: dict[str, object], exclude_fields: tuple[str, ...], expected: dict[str, str]
) -> None:
    """Each required field submitted without a value has a "required" error."""
    errors = validate_input_fields(
        user_input, INPUT_FIELDS["limits"], FIELD_SCHEMA["limits"], exclude_fields=exclude_fields
    )

    assert errors == expected


def test_validate_input_fields_force_required() -> None:
    """An optional field forced required needs a value."""
    field = replace(PRICE, force_required=True)

    assert validate_input_fields({"price": as_none_value()}, {"price": field}, {"price": OPTIONAL}) == {
        "price": "required"
    }


def test_validate_input_fields_requires_schema_metadata() -> None:
    """A field the element's schema does not describe is a coding error."""
    with pytest.raises(RuntimeError, match="Missing schema metadata"):
        validate_input_fields({}, {"power": POWER}, {})


@pytest.mark.parametrize(
    ("user_input", "expected"),
    [
        pytest.param({"limits": {"power": as_constant_value(1.0)}, "options": {}}, {}, id="valid"),
        pytest.param({"limits": {"power": as_none_value()}, "options": {}}, {"limits": "required"}, id="by_section"),
        pytest.param({"limits": "invalid"}, {}, id="non_mapping_section"),
    ],
)
def test_validate_sectioned_input_fields(user_input: dict[str, object], expected: dict[str, str]) -> None:
    """Errors are keyed by the section holding the field, as Home Assistant only shows top-level errors."""
    assert validate_sectioned_input_fields(user_input, INPUT_FIELDS, FIELD_SCHEMA, SECTIONS) == expected


def test_convert_sectioned_input_to_config() -> None:
    """Each section's submitted values are stored as given, leaving out excluded fields."""
    config = convert_sectioned_input_to_config(
        {
            "name": "Battery",
            "limits": {"power": as_constant_value(1.0), "price": as_entity_value(["sensor.price"])},
            "options": "invalid",
        },
        SECTIONS,
        exclude_fields=("price",),
    )

    assert config == {"limits": {"power": as_constant_value(1.0)}, "options": {}}


def test_selectors_are_input_selectors() -> None:
    """Every input field entry is an input selector offering its inclusion map's entities."""
    entries = build_input_field_entries(
        {"window_calendar": _calendar_field()},
        field_schema={"window_calendar": FieldSchemaInfo(value_type=EntityValue, is_optional=False)},
        inclusion_map={"window_calendar": ["calendar.pool_pump"]},
    )

    _marker, selector = entries["window_calendar"]
    assert isinstance(selector, InputSelector)
    assert selector.config["kinds"] == ["entity"]
    assert selector.config["entities"] == ["calendar.pool_pump"]
