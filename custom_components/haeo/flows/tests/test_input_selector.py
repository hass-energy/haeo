"""Tests for the input selector behind every HAEO input field."""

from homeassistant.helpers import config_validation as cv
import pytest
import voluptuous as vol
import voluptuous_serialize

from custom_components.haeo.core.schema import SchemaValue, as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.flows.input_selector import INPUT_SELECTOR_TYPE, InputSelector, InputSelectorConfig

NUMBER_CONFIG: InputSelectorConfig = {
    "kinds": ["entity", "constant", "none"],
    "value_type": "number",
    "domains": ["sensor"],
    "entities": ["sensor.a", "sensor.b", "sensor.charger"],
    "min": 0.0,
    "max": 100.0,
}


def _selector(**overrides: object) -> InputSelector:
    """Build a selector from the number config, leaving out keys overridden with None."""
    config = {**NUMBER_CONFIG, **overrides}
    return InputSelector({key: value for key, value in config.items() if value is not None})


@pytest.mark.parametrize(
    "config",
    [
        pytest.param({**NUMBER_CONFIG, "kinds": ["connection_target"]}, id="unknown_kind"),
        pytest.param({**NUMBER_CONFIG, "value_type": "text"}, id="unknown_value_type"),
        pytest.param({**NUMBER_CONFIG, "min": "low"}, id="non_numeric_limit"),
        pytest.param({key: value for key, value in NUMBER_CONFIG.items() if key != "domains"}, id="missing_domains"),
    ],
)
def test_config_schema_rejects_invalid_configs(config: dict[str, object]) -> None:
    """A selector config offers only known kinds and value types, with numeric limits and its domains."""
    with pytest.raises(vol.Invalid):
        InputSelector(config)


def test_config_schema_coerces_limits_to_floats() -> None:
    """Numeric limits are stored as floats."""
    selector = _selector(min=1, max="5", step=1)

    assert selector.config == {**NUMBER_CONFIG, "min": 1.0, "max": 5.0, "step": 1.0}


@pytest.mark.parametrize(
    ("overrides", "data", "expected"),
    [
        pytest.param(
            {},
            {"type": "entity", "value": ["sensor.a", "sensor.b"]},
            as_entity_value(["sensor.a", "sensor.b"]),
            id="entity_list",
        ),
        pytest.param({}, {"type": "entity", "value": "sensor.a"}, as_entity_value(["sensor.a"]), id="entity_string"),
        pytest.param(
            {"entities": None},
            {"type": "entity", "value": ["sensor.anything"]},
            as_entity_value(["sensor.anything"]),
            id="any_entity_in_the_domains",
        ),
        pytest.param({}, {"type": "entity", "value": []}, as_none_value(), id="empty_entity_list"),
        pytest.param({}, {"type": "constant", "value": 10}, as_constant_value(10.0), id="number"),
        pytest.param({}, {"type": "constant", "value": "2.5"}, as_constant_value(2.5), id="number_string"),
        pytest.param({}, {"type": "constant", "value": 0}, as_constant_value(0.0), id="number_at_min"),
        pytest.param({}, {"type": "constant", "value": 100}, as_constant_value(100.0), id="number_at_max"),
        pytest.param({"value_type": "boolean"}, {"type": "constant", "value": True}, as_constant_value(True), id="on"),
        pytest.param(
            {"value_type": "boolean"}, {"type": "constant", "value": "off"}, as_constant_value(False), id="off_string"
        ),
        pytest.param({}, {"type": "none"}, as_none_value(), id="none"),
        pytest.param({"kinds": ["entity"]}, {"type": "none"}, as_none_value(), id="none_when_not_offered"),
    ],
)
def test_call_returns_the_stored_value(
    overrides: dict[str, object], data: dict[str, object], expected: SchemaValue
) -> None:
    """A submitted value is returned in the form HAEO stores, with an empty entity list as no value.

    Whether a field may be left without a value is the flow's to check, so none is always accepted.
    """
    assert _selector(**overrides)(data) == expected


@pytest.mark.parametrize(
    ("overrides", "data"),
    [
        pytest.param(
            {"kinds": ["constant", "none"]}, {"type": "entity", "value": ["sensor.a"]}, id="entity_not_offered"
        ),
        pytest.param({"kinds": ["entity", "none"]}, {"type": "constant", "value": 1.0}, id="constant_not_offered"),
        pytest.param({}, {"type": "connection_target", "value": "battery"}, id="unknown_kind"),
        pytest.param({}, {"value": 1.0}, id="no_kind"),
        pytest.param({}, {"type": "entity", "value": ["sensor.a", "sensor.other"]}, id="entity_not_listed"),
        pytest.param({"entities": None}, {"type": "entity", "value": ["light.lamp"]}, id="entity_outside_domains"),
        pytest.param({}, {"type": "entity", "value": ["not an entity"]}, id="invalid_entity_id"),
        pytest.param({}, {"type": "constant", "value": -1.0}, id="below_min"),
        pytest.param({}, {"type": "constant", "value": 100.5}, id="above_max"),
        pytest.param({}, {"type": "constant", "value": "lots"}, id="not_a_number"),
        pytest.param({"value_type": "boolean"}, {"type": "constant", "value": "maybe"}, id="not_a_boolean"),
        pytest.param({}, ["sensor.a"], id="list"),
        pytest.param({}, "sensor.a", id="string"),
        pytest.param({}, None, id="missing"),
    ],
)
def test_call_rejects_values_the_config_does_not_offer(overrides: dict[str, object], data: object) -> None:
    """A value of a kind or entity the field does not offer, out of range, or not a mapping is rejected."""
    with pytest.raises(vol.Invalid):
        _selector(**overrides)(data)


def test_number_without_limits_accepts_any_number() -> None:
    """A number field without limits takes any number."""
    selector = InputSelector({"kinds": ["constant"], "value_type": "number", "domains": []})

    assert selector({"type": "constant", "value": -1e6}) == as_constant_value(-1e6)


def test_serialize_sends_the_config_under_its_selector_type() -> None:
    """The form sends the selector's config to the frontend element named by its type."""
    schema = vol.Schema({vol.Required("power"): _selector()})

    serialized = voluptuous_serialize.convert(schema, custom_serializer=cv.custom_serializer)

    assert serialized == [{"name": "power", "required": True, "selector": {INPUT_SELECTOR_TYPE: NUMBER_CONFIG}}]


def test_call_keeps_the_states_an_entity_value_lists() -> None:
    """The words an entity reports for on and off survive the form unchanged."""
    stored = as_entity_value(["sensor.charger"], on_states=["Charging"], off_states=["Idle"])

    assert _selector()({**stored, "value": ["sensor.charger"]}) == stored
