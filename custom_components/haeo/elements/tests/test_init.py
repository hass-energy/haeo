"""Tests for elements module __init__.py functions."""

from collections.abc import Mapping
from importlib import import_module
from types import MappingProxyType
from typing import Any, Literal, TypeAliasType, TypedDict, get_type_hints, is_typeddict

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant

from custom_components.haeo import elements as elements_module
from custom_components.haeo.const import CONF_INTEGRATION_TYPE, DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_connection_target, as_constant_value
from custom_components.haeo.core.schema.elements import ELEMENT_CONFIG_SCHEMAS, ElementType, battery, connection
from custom_components.haeo.core.schema.elements.policy import CONF_ENABLED, CONF_RULES
from custom_components.haeo.elements import (
    collect_element_subentries,
    get_input_field_schema_info,
    get_input_fields,
    get_list_input_fields,
)
from custom_components.haeo.core.schema.elements.conformance import is_element_config_schema

# Each element type's valid flow configs, as its subentry stores them
VALID_CONFIGS = [
    pytest.param(
        element_type,
        {CONF_ELEMENT_TYPE: element_type, **case["config"]},
        id=f"{element_type}: {case['description']}",
    )
    for element_type in ELEMENT_TYPES
    for case in import_module(f"custom_components.haeo.flows.tests.test_data.{element_type}").VALID_DATA
]


@pytest.mark.parametrize(
    "input_data",
    [
        [1, 2, 3],
        "not a config",
        None,
    ],
)
def test_is_not_element_config_schema(input_data: Any) -> None:
    """Test is_element_config_schema with non-Mapping input."""
    assert is_element_config_schema(input_data) is False


@pytest.mark.parametrize(
    "input_data",
    [
        {"element_type": "unknown_type", "name": "test"},  # Unknown element type
        {"name": "test"},  # Missing element_type
        {"element_type": "battery"},  # Missing all required fields
        {
            "element_type": "battery",
            "name": "test",
        },  # Missing required battery fields
        {
            "element_type": "connection",
            "name": "test",
            connection.SECTION_ENDPOINTS: {"source": as_connection_target("a")},
        },  # Missing target
    ],
)
def test_is_element_config_schema_invalid_structure(input_data: dict[str, Any]) -> None:
    """Test is_element_config_schema with invalid element structure."""
    assert is_element_config_schema(input_data) is False


def _without_optional_fields(element_type: ElementType, config: Mapping[str, object]) -> dict[str, object]:
    """Return the config with every optional field removed, at the top level and inside each section."""
    schema = ELEMENT_CONFIG_SCHEMAS[element_type]
    hints = get_type_hints(schema)
    minimal: dict[str, object] = {}
    for key, value in config.items():
        if key in schema.__optional_keys__:
            continue
        section = hints[key]
        if isinstance(section, TypeAliasType):
            section = section.__value__
        if is_typeddict(section) and isinstance(value, Mapping):
            value = {field: item for field, item in value.items() if field not in section.__optional_keys__}
        minimal[key] = value
    return minimal


@pytest.mark.parametrize("element_type", ELEMENT_TYPES)
def test_every_element_type_has_valid_configs(element_type: ElementType) -> None:
    """Each registered element type has valid configs for the schema tests below."""
    assert any(param.values[0] == element_type for param in VALID_CONFIGS)


@pytest.mark.parametrize(("element_type", "config"), VALID_CONFIGS)
def test_is_element_config_schema_accepts_valid_config(element_type: ElementType, config: dict[str, object]) -> None:
    """A config as the element's flow stores it is valid."""
    assert config[CONF_ELEMENT_TYPE] == element_type
    assert is_element_config_schema(config) is True


@pytest.mark.parametrize(("element_type", "config"), VALID_CONFIGS)
def test_is_element_config_schema_accepts_config_without_optional_fields(element_type: ElementType, config: dict[str, object]) -> None:
    """Omitting every optional field, including those inside sections, leaves a config valid."""
    assert is_element_config_schema(_without_optional_fields(element_type, config)) is True


@pytest.mark.parametrize(("element_type", "config"), VALID_CONFIGS)
def test_is_element_config_schema_rejects_config_missing_a_required_key(element_type: ElementType, config: dict[str, object]) -> None:
    """Removing any required top-level key, such as a required section, makes a config invalid."""
    for key in ELEMENT_CONFIG_SCHEMAS[element_type].__required_keys__:
        incomplete = {name: value for name, value in config.items() if name != key}
        assert is_element_config_schema(incomplete) is False, key


def test_collect_element_subentries_skips_invalid_configs(
    hass: HomeAssistant,
) -> None:
    """collect_element_subentries should warn and skip invalid subentries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Network",
        },
        entry_id="hub_entry_id",
    )
    entry.add_to_hass(hass)

    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
                CONF_NAME: "Bad Battery",
            }
        ),
        subentry_type=battery.ELEMENT_TYPE,
        title="Bad Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, subentry)

    result = collect_element_subentries(entry)

    assert result == []


def test_config_schemas_match_element_types() -> None:
    """Ensure ELEMENT_CONFIG_SCHEMAS has an entry for every registered element type."""
    for element_type in ELEMENT_TYPES:
        assert element_type in ELEMENT_CONFIG_SCHEMAS, f"Missing config schema for {element_type}"


class _DummySection(TypedDict):
    field: str


DummySectionAlias = TypeAliasType("DummySectionAlias", _DummySection)


class _DummySchema(TypedDict):
    element_type: Literal[ElementType.BATTERY]
    dummy: DummySectionAlias


def test_get_input_field_schema_info_marks_optional_fields() -> None:
    """get_input_field_schema_info marks NotRequired fields as optional."""
    input_fields = get_input_fields(battery.ELEMENT_TYPE)
    schema_info = get_input_field_schema_info(battery.ELEMENT_TYPE, input_fields)

    assert schema_info[battery.SECTION_STORAGE][battery.CONF_CAPACITY].is_optional is False
    assert schema_info[battery.SECTION_LIMITS][battery.CONF_MIN_CHARGE_PERCENTAGE].is_optional is True
    assert schema_info[battery.SECTION_PRICING][battery.CONF_SALVAGE_VALUE].is_optional is True


def test_get_input_field_schema_info_missing_section() -> None:
    """get_input_field_schema_info raises when section is missing."""
    input_fields = dict(get_input_fields(battery.ELEMENT_TYPE))
    input_fields["missing_section"] = {}

    with pytest.raises(RuntimeError, match="Section 'missing_section' not found"):
        get_input_field_schema_info(battery.ELEMENT_TYPE, input_fields)


def test_get_input_field_schema_info_section_not_typed_dict() -> None:
    """get_input_field_schema_info raises when section is not a TypedDict."""
    input_fields = get_input_fields(battery.ELEMENT_TYPE)
    sample_field = input_fields[battery.SECTION_STORAGE][battery.CONF_CAPACITY]

    with pytest.raises(RuntimeError, match="Section 'element_type'.*not a TypedDict"):
        get_input_field_schema_info(
            battery.ELEMENT_TYPE,
            {"element_type": {"field": sample_field}},
        )


def test_get_input_field_schema_info_missing_field() -> None:
    """get_input_field_schema_info raises when a field is missing in schema."""
    input_fields = get_input_fields(battery.ELEMENT_TYPE)
    sample_field = input_fields[battery.SECTION_STORAGE][battery.CONF_CAPACITY]

    with pytest.raises(RuntimeError, match="Field 'storage.missing_field' not found"):
        get_input_field_schema_info(
            battery.ELEMENT_TYPE,
            {battery.SECTION_STORAGE: {"missing_field": sample_field}},
        )


def test_get_input_field_schema_info_type_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_input_field_schema_info unwraps TypeAliasType sections."""
    original_get_type_hints = elements_module.get_type_hints

    def _fake_get_type_hints(schema_cls: type) -> dict[str, object]:
        if schema_cls is _DummySchema:
            return {"dummy": DummySectionAlias}
        if schema_cls is _DummySection:
            return {"field": str}
        return original_get_type_hints(schema_cls)

    input_fields = get_input_fields(battery.ELEMENT_TYPE)
    sample_field = input_fields[battery.SECTION_STORAGE][battery.CONF_CAPACITY]

    monkeypatch.setattr(elements_module, "get_type_hints", _fake_get_type_hints)
    monkeypatch.setitem(elements_module.ELEMENT_CONFIG_SCHEMAS, battery.ELEMENT_TYPE, _DummySchema)

    schema_info = get_input_field_schema_info(
        battery.ELEMENT_TYPE,
        {"dummy": {"field": sample_field}},
    )

    assert schema_info["dummy"]["field"].is_optional is False


def test_get_list_input_fields_empty_for_unknown_element_type() -> None:
    """Invalid element_type yields no dynamic list fields."""
    assert get_list_input_fields({CONF_ELEMENT_TYPE: "not_an_element"}) == {}


def test_get_list_input_fields_skips_non_sequence_list_items() -> None:
    """List hint keys that are not list/tuple are ignored."""
    cfg = {
        CONF_ELEMENT_TYPE: ElementType.POLICY,
        "name": "Policies",
        CONF_RULES: "not-a-list",
    }
    assert get_list_input_fields(cfg) == {}


def test_get_list_input_fields_builds_policy_rule_fields() -> None:
    """Policy rules list produces per-item field definitions."""
    cfg = {
        CONF_ELEMENT_TYPE: ElementType.POLICY,
        "name": "Policies",
        CONF_RULES: [
            {"name": "Export", CONF_ENABLED: True, "price": as_constant_value(0.05)},
        ],
    }
    groups = get_list_input_fields(cfg)
    assert f"{CONF_RULES}.0" in groups
    assert CONF_ENABLED in groups[f"{CONF_RULES}.0"]
    assert "price" in groups[f"{CONF_RULES}.0"]
