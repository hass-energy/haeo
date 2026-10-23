"""Test that en.json translates every key the integration uses, and nothing else.

Each case derives the keys the integration uses from the same registries that
create its entities, devices, and flows, from the code its flows reach, or from
the forms its flows show, then compares them with en.json: a missing key shows
a raw key to users, and an unused one is a string nobody reads.
"""

from collections.abc import Awaitable, Callable, Iterator, Mapping
from copy import deepcopy
from dataclasses import dataclass
from functools import cache
from importlib import import_module
import types
from types import MappingProxyType

# Reflection over typing constructs (aliases, unions, generics); the typing
# introspection API is inherently dynamic.
from typing import Any, Union, get_args, get_origin, get_type_hints  # noqa: TID251
from unittest.mock import Mock

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    SOURCE_USER,
    ConfigSubentry,
    ConfigSubentryFlow,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult, FlowResultType
from homeassistant.helpers.entity import Entity
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import PLATFORMS
from custom_components.haeo.const import CONF_INTEGRATION_TYPE, DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.coordinator import STATUS_OPTIONS
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.const import (
    CONF_ADVANCED_MODE,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON,
    CONF_NAME,
    HORIZON_PRESET_2_DAYS,
)
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import ELEMENTS
from custom_components.haeo.core.model.reactive import OutputMethod
from custom_components.haeo.core.schema import VALUE_TYPE_ENTITY, get_schema_value_kinds
from custom_components.haeo.core.schema.elements import ELEMENT_CONFIG_SCHEMAS, ElementType
from custom_components.haeo.core.schema.field_hints import extract_list_field_hints
from custom_components.haeo.core.schema.horizon_value import as_horizon_preset_value
from custom_components.haeo.elements import (
    ELEMENT_DEVICE_NAMES,
    ELEMENT_OUTPUT_NAMES,
    get_input_field_schema_info,
    get_input_fields,
    get_surfaced_input_fields,
    iter_input_field_paths,
)
from custom_components.haeo.elements.field_hints import build_list_input_fields
from custom_components.haeo.flows import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON, get_element_flow_classes
from custom_components.haeo.flows.elements.policy import ACTION_EDIT, CONF_ACTION, CONF_RULE
from custom_components.haeo.flows.hub import HubConfigFlow
from custom_components.haeo.translations.tests.flow_messages import flow_messages
from custom_components.haeo.translations.tests.runtime_checks import TranslationPath, form_labels, translation


def _is_mapping_type(annotation: Any) -> bool:
    try:
        alias_value = annotation.__value__
    except AttributeError:
        alias_value = None
    if alias_value is not None:
        return _is_mapping_type(alias_value)
    origin = get_origin(annotation)
    if origin is None:
        return annotation in (Mapping, dict)
    if origin in (Mapping, dict):
        return True
    if origin in (types.UnionType, Union):
        return any(_is_mapping_type(arg) for arg in get_args(annotation))
    return False


def _mapping_output_names() -> set[str]:
    """Return the outputs that hold one value per participant rather than a sensor of their own."""
    mapping_outputs: set[str] = set()
    for element_spec in ELEMENTS.values():
        element_class = element_spec.factory
        for name in dir(element_class):
            attr = getattr(element_class, name, None)
            if not isinstance(attr, OutputMethod):
                continue
            output_fn = getattr(attr, "_fn", None)
            if output_fn is None:
                continue
            return_type = get_type_hints(output_fn).get("return")
            if return_type is None:
                continue
            if _is_mapping_type(return_type):
                mapping_outputs.add(attr.output_name)
    return mapping_outputs


def _platform(cls: type) -> str:
    """Return the entity platform a Home Assistant entity class belongs to."""
    return next(
        base.__module__.split(".")[2] for base in cls.__mro__ if base.__module__.startswith("homeassistant.components.")
    )


def _subclasses(cls: type) -> Iterator[type]:
    for subclass in cls.__subclasses__():
        yield subclass
        yield from _subclasses(subclass)


def _class_attr(cls: type, name: str) -> object:
    """Return the class-level value of an entity's ``_attr_`` attribute.

    Home Assistant's entity metaclass moves a class-level ``_attr_name`` to ``__attr_name``.
    """
    return getattr(cls, f"__attr_{name}", None)


def _entity_classes() -> dict[str, type[Entity]]:
    """Return the integration's entity classes that set their own translation key, by that key."""
    # The platform modules define the entity classes
    for platform in PLATFORMS:
        import_module(f"custom_components.haeo.{platform}")
    return {
        str(_class_attr(cls, "translation_key")): cls
        for cls in _subclasses(Entity)
        if cls.__module__.startswith("custom_components.haeo.")
        and ".tests." not in cls.__module__
        and "__attr_translation_key" in vars(cls)
    }


def _input_field_keys() -> dict[str, set[str]]:
    """Return the translation keys of every input entity, by platform."""
    keys: dict[str, set[str]] = {}
    for element_type in ELEMENT_TYPES:
        groups = dict(get_input_fields(element_type))
        for list_key, hints in extract_list_field_hints(ELEMENT_CONFIG_SCHEMAS[element_type]).items():
            groups.update(build_list_input_fields(element_type, list_key, hints, [{}]))
        fields = [info for _, info in iter_input_field_paths(groups)]
        fields.extend(get_surfaced_input_fields(element_type).values())
        for info in fields:
            description = info.entity_description
            # Entity description classes are generated at runtime by Home Assistant's
            # frozen dataclass shim, so only their name says which platform they are for
            platform = type(description).__name__.removesuffix("EntityDescription").lower()
            keys.setdefault(platform, set()).add(str(description.translation_key))
    return keys


def _entity_keys() -> dict[str, set[str]]:
    """Return the translation key of every entity the integration creates, by platform."""
    keys = _input_field_keys()
    keys.setdefault("sensor", set()).update(str(name) for name in ELEMENT_OUTPUT_NAMES)
    keys["sensor"] -= _mapping_output_names()
    for key, cls in _entity_classes().items():
        keys.setdefault(_platform(cls), set()).add(key)
    return keys


def _enum_sensor_states() -> set[str]:
    """Return ``key.state`` for every state of every enum sensor whose class sets its translation key.

    Every enum sensor reports an optimization status, so its states are the
    status options. Output sensors only learn their type from the optimization,
    so the runtime checks cover their states.
    """
    return {
        f"{key}.{state}"
        for key, cls in _entity_classes().items()
        if _class_attr(cls, "device_class") == SensorDeviceClass.ENUM
        for state in STATUS_OPTIONS
    }


def _flow_classes() -> dict[TranslationPath, type]:
    """Return every flow handler the integration registers, by where its strings live in en.json."""
    options_flow = get_type_hints(HubConfigFlow.async_get_options_flow)["return"]
    return {
        ("config",): HubConfigFlow,
        ("options",): options_flow,
        **{("config_subentries", str(et)): flow for et, flow in get_element_flow_classes().items()},
    }


def _keys(path: TranslationPath) -> set[str]:
    node = translation(path)
    return set(node) if isinstance(node, Mapping) else set()


@dataclass(frozen=True)
class Comparison:
    """Keys the integration uses under an en.json path, and the keys en.json has there."""

    used: set[str]
    translated: set[str]
    # Flow analysis over-approximates what a flow shows, so it can only find unused keys
    report_missing: bool = True


def _flow_prefixes() -> list[TranslationPath]:
    return sorted(set(_flow_classes()) | {("config_subentries", key) for key in _keys(("config_subentries",))})


FLOW_KINDS = {"error": "errors", "abort": "aborts", "step": "steps"}


def _case_paths() -> list[str]:
    """Return the en.json path of every comparison, without building any of them."""
    platforms = {str(platform) for platform in PLATFORMS} | _keys(("entity",))
    return [
        *(f"entity.{platform}" for platform in sorted(platforms)),
        "entity.sensor.*.state",
        "device",
        *(".".join((*prefix, kind)) for prefix in _flow_prefixes() for kind in FLOW_KINDS),
    ]


@cache
def _comparisons() -> dict[str, Comparison]:
    entity_keys = _entity_keys()
    comparisons = {
        f"entity.{platform}": Comparison(entity_keys.get(platform, set()), _keys(("entity", platform)))
        for platform in {str(platform) for platform in PLATFORMS} | _keys(("entity",))
    }
    comparisons["entity.sensor.*.state"] = Comparison(
        _enum_sensor_states(),
        {
            f"{key}.{state}"
            for key in _keys(("entity", "sensor"))
            for state in _keys(("entity", "sensor", key, "state"))
        },
    )
    comparisons["device"] = Comparison({str(name) for name in ELEMENT_DEVICE_NAMES}, _keys(("device",)))
    flows = _flow_classes()
    for prefix in _flow_prefixes():
        messages = flow_messages(flows[prefix]) if prefix in flows else None
        for kind, attribute in FLOW_KINDS.items():
            path = (*prefix, kind)
            used: set[str] = getattr(messages, attribute) if messages is not None else set()
            comparisons[".".join(path)] = Comparison(used, _keys(path), report_missing=False)
    return comparisons


@pytest.mark.parametrize("path", _case_paths())
def test_translations_match_used_keys(path: str) -> None:
    """En.json translates every key the integration uses under a path, and no others."""
    comparison = _comparisons()[path]
    missing = comparison.used - comparison.translated if comparison.report_missing else set()

    assert {
        "missing": sorted(missing),
        "unused": sorted(comparison.translated - comparison.used),
    } == {"missing": [], "unused": []}, f"Translation keys under {path} do not match what the integration uses"


def _leaf_paths(node: object, prefix: TranslationPath = ()) -> set[TranslationPath]:
    if not isinstance(node, Mapping):
        return {prefix}
    return set().union(*(_leaf_paths(child, (*prefix, str(key))) for key, child in node.items()))


@pytest.fixture
def hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a hub entry offering every element type."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            HUB_SECTION_COMMON: {CONF_NAME: "Test Hub", CONF_HORIZON: as_horizon_preset_value(HORIZON_PRESET_2_DAYS)},
            HUB_SECTION_ADVANCED: {CONF_ADVANCED_MODE: True},
        },
    )
    entry.add_to_hass(hass)
    return entry


def _create_flow(hass: HomeAssistant, hub_entry: MockConfigEntry, prefix: TranslationPath, source: str) -> Any:
    """Return a flow handler wired to the hub as Home Assistant would start it."""
    flow: Any = _flow_classes()[prefix]()
    flow.hass = hass
    flow.context = {"source": source}
    if isinstance(flow, ConfigSubentryFlow):
        flow.handler = (hub_entry.entry_id, prefix[-1])
    elif isinstance(flow, OptionsFlow):
        flow.handler = hub_entry.entry_id
    else:
        flow.handler = DOMAIN
    return flow


def _valid_config(prefix: TranslationPath) -> dict[str, Any]:
    """Return the first valid configuration in an element flow's test data."""
    module = import_module(f"custom_components.haeo.flows.tests.test_data.{prefix[-1]}")
    return deepcopy(module.VALID_DATA[0]["config"])


async def _first_form(hass: HomeAssistant, hub_entry: MockConfigEntry, prefix: TranslationPath) -> FlowResult:
    flow = _create_flow(hass, hub_entry, prefix, SOURCE_USER)
    step_id = flow.init_step if isinstance(flow, OptionsFlow) else SOURCE_USER
    return await getattr(flow, f"async_step_{step_id}")(None)


async def _states_form(hass: HomeAssistant, hub_entry: MockConfigEntry, prefix: TranslationPath) -> FlowResult:
    """Submit an element whose on/off input reads a sensor reporting words."""
    element_type = ElementType(prefix[-1])
    input_fields = get_input_fields(element_type)
    schema_info = get_input_field_schema_info(element_type, input_fields)
    section, field_name = next(
        (section, field_name)
        for section, fields in input_fields.items()
        for field_name, info in fields.items()
        if info.output_type is OutputType.STATUS
        and VALUE_TYPE_ENTITY in get_schema_value_kinds(schema_info[section][field_name].value_type)
    )
    hass.states.async_set("sensor.reports_words", "Idle", {"options": ["Idle", "Charging"]})
    user_input = _valid_config(prefix)
    user_input[section] = {**user_input.get(section, {}), field_name: ["sensor.reports_words"]}
    return await _create_flow(hass, hub_entry, prefix, SOURCE_USER).async_step_user(user_input)


async def _reconfigure_flow(hass: HomeAssistant, hub_entry: MockConfigEntry, prefix: TranslationPath) -> Any:
    """Return a flow reconfiguring an element saved from its test data, showing its first form."""
    config = {CONF_ELEMENT_TYPE: prefix[-1], CONF_NAME: prefix[-1], **_valid_config(prefix)}
    subentry = ConfigSubentry(data=MappingProxyType(config), subentry_type=prefix[-1], title=prefix[-1], unique_id=None)
    hass.config_entries.async_add_subentry(hub_entry, subentry)
    flow = _create_flow(hass, hub_entry, prefix, SOURCE_RECONFIGURE)
    flow.context["subentry_id"] = subentry.subentry_id
    flow._get_reconfigure_subentry = Mock(return_value=subentry)
    await flow.async_step_reconfigure(None)
    return flow


async def _reconfigure_form(hass: HomeAssistant, hub_entry: MockConfigEntry, prefix: TranslationPath) -> FlowResult:
    """Show the reconfigure form of the hub, or of an element saved from its test data."""
    if issubclass(_flow_classes()[prefix], ConfigSubentryFlow):
        flow = await _reconfigure_flow(hass, hub_entry, prefix)
    else:
        flow = _create_flow(hass, hub_entry, prefix, SOURCE_RECONFIGURE)
        flow.context["entry_id"] = hub_entry.entry_id
    return await flow.async_step_reconfigure(None)


async def _edit_rule_form(hass: HomeAssistant, hub_entry: MockConfigEntry, prefix: TranslationPath) -> FlowResult:
    flow = await _reconfigure_flow(hass, hub_entry, prefix)
    return await flow.async_step_reconfigure({CONF_RULE: "0", CONF_ACTION: ACTION_EDIT})


type FormRenderer = Callable[[HomeAssistant, MockConfigEntry, TranslationPath], Awaitable[FlowResult]]

# How to reach each step, by step id
STEP_RENDERERS: dict[str, FormRenderer] = {
    "init": _first_form,
    "user": _first_form,
    "states": _states_form,
    "reconfigure": _reconfigure_form,
    "edit_rule": _edit_rule_form,
}


def _translated_steps() -> list[tuple[TranslationPath, str]]:
    return [(prefix, step_id) for prefix in sorted(_flow_classes()) for step_id in sorted(_keys((*prefix, "step")))]


@pytest.mark.parametrize(
    ("prefix", "step_id"), _translated_steps(), ids=lambda value: ".".join(value) if isinstance(value, tuple) else value
)
async def test_step_strings_match_its_form(
    hass: HomeAssistant, hub_entry: MockConfigEntry, prefix: TranslationPath, step_id: str
) -> None:
    """En.json labels every field and section of a step's form, and describes nothing the form lacks."""
    result = await STEP_RENDERERS[step_id](hass, hub_entry, prefix)

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == step_id
    schema = result.get("data_schema")
    assert schema is not None
    labels = set(form_labels(schema))
    descriptions = {(*path[:-2], "data_description", path[-1]) for path in labels if path[-2] == "data"}
    translated = _leaf_paths(translation((*prefix, "step", step_id))) - {("title",), ("description",)}
    assert {
        "missing": sorted(".".join(path) for path in labels - translated),
        "unused": sorted(".".join(path) for path in translated - labels - descriptions),
    } == {"missing": [], "unused": []}
