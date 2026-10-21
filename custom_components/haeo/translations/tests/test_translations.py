"""Test that en.json translates every key the integration uses, and nothing else.

Each case derives the keys the integration uses from the same registries that
create its entities, devices, and flows, or from the forms its flows show, then
compares them with en.json in both directions: a missing key shows a raw key to
users, and an unused one is a string nobody reads.
"""

import ast
from collections.abc import Iterator, Mapping
from functools import cache
import inspect
import sys
import types

# Reflection over typing constructs (aliases, unions, generics); the typing
# introspection API is inherently dynamic.
from typing import Any, Union, get_args, get_origin, get_type_hints  # noqa: TID251

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import SOURCE_USER, ConfigSubentryFlow, OptionsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import number, sensor, switch
from custom_components.haeo.const import CONF_INTEGRATION_TYPE, DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.const import CONF_ADVANCED_MODE, CONF_HORIZON, CONF_NAME, HORIZON_PRESET_2_DAYS
from custom_components.haeo.core.model.elements import ELEMENTS
from custom_components.haeo.core.model.reactive import OutputMethod
from custom_components.haeo.core.schema.elements import ELEMENT_CONFIG_SCHEMAS
from custom_components.haeo.core.schema.field_hints import extract_list_field_hints
from custom_components.haeo.core.schema.horizon_value import as_horizon_preset_value
from custom_components.haeo.elements import (
    ELEMENT_DEVICE_NAMES,
    ELEMENT_OUTPUT_NAMES,
    get_input_fields,
    get_surfaced_input_fields,
    iter_input_field_paths,
)
from custom_components.haeo.elements.field_hints import build_list_input_fields
from custom_components.haeo.flows import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON, get_element_flow_classes
from custom_components.haeo.flows.hub import HubConfigFlow
from custom_components.haeo.translations.tests.runtime_checks import TranslationPath, form_labels, translation

# The entity platforms define the entity classes this test inspects
PLATFORM_MODULES = (number, sensor, switch)


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


def _enum_sensor_states() -> dict[str, set[str]]:
    """Return the states of every enum sensor, by translation key."""
    return {
        key: set(options)
        for key, cls in _entity_classes().items()
        if _class_attr(cls, "device_class") == SensorDeviceClass.ENUM
        and isinstance(options := _class_attr(cls, "options"), list)
    }


def _flow_classes() -> dict[TranslationPath, type]:
    """Return every flow handler the integration registers, by where its strings live in en.json."""
    options_flow = get_type_hints(HubConfigFlow.async_get_options_flow)["return"]
    return {
        ("config",): HubConfigFlow,
        ("options",): options_flow,
        **{("config_subentries", str(et)): flow for et, flow in get_element_flow_classes().items()},
    }


@cache
def _string_literals(module: types.ModuleType) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    literals = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    return literals | {value for value in vars(module).values() if isinstance(value, str)}


def _flow_strings(flow: type) -> set[str]:
    """Return every string the modules a flow is built from could pass as an error or abort reason.

    That is the module of each class the flow inherits from, and of each
    integration function and class those modules import.
    """
    modules = {sys.modules[cls.__module__] for cls in flow.__mro__ if cls is not object}
    imported = {
        sys.modules[value.__module__]
        for module in modules
        for value in vars(module).values()
        if (inspect.isfunction(value) or inspect.isclass(value)) and value.__module__.startswith("custom_components.")
    }
    return set().union(*(_string_literals(module) for module in modules | imported))


def _keys(path: TranslationPath) -> set[str]:
    node = translation(path)
    return set(node) if isinstance(node, Mapping) else set()


def _cases() -> Iterator[tuple[str, set[str], set[str]]]:
    """Yield (en.json path, keys the integration uses there, keys en.json has there) for each comparison.

    Which errors and aborts a flow shows is only known as it runs, so the
    runtime checks report missing ones; here a flow uses a key under its
    error or abort path when one of the modules it is built from names it.
    """
    entity_keys = _entity_keys()
    for platform in sorted(set(entity_keys) | _keys(("entity",))):
        yield f"entity.{platform}", entity_keys.get(platform, set()), _keys(("entity", platform))
    yield (
        "entity.sensor.*.state",
        {f"{key}.{state}" for key, states in _enum_sensor_states().items() for state in states},
        {
            f"{key}.{state}"
            for key in _keys(("entity", "sensor"))
            for state in _keys(("entity", "sensor", key, "state"))
        },
    )
    yield "device", {str(name) for name in ELEMENT_DEVICE_NAMES}, _keys(("device",))
    flows = _flow_classes()
    prefixes = set(flows) | {("config_subentries", key) for key in _keys(("config_subentries",))}
    for prefix in sorted(prefixes):
        flow_strings = _flow_strings(flows[prefix]) if prefix in flows else set()
        for kind in ("error", "abort"):
            path = (*prefix, kind)
            yield ".".join(path), _keys(path) & flow_strings, _keys(path)


CASES = list(_cases())


@pytest.mark.parametrize(("path", "used", "translated"), CASES, ids=[case[0] for case in CASES])
def test_translations_match_used_keys(path: str, used: set[str], translated: set[str]) -> None:
    """En.json translates every key the integration uses under a path, and no others."""
    assert {
        "missing": sorted(used - translated),
        "unused": sorted(translated - used),
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


FLOWS = _flow_classes()


@pytest.mark.parametrize("prefix", sorted(FLOWS), ids=".".join)
async def test_first_form_strings_match_its_fields(
    hass: HomeAssistant, hub_entry: MockConfigEntry, prefix: TranslationPath
) -> None:
    """En.json labels every field and section of a flow's first form, and describes nothing the form lacks."""
    flow = FLOWS[prefix]()
    flow.hass = hass
    flow.context = {"source": SOURCE_USER}
    if isinstance(flow, ConfigSubentryFlow):
        flow.handler = (hub_entry.entry_id, prefix[-1])
    elif isinstance(flow, OptionsFlow):
        flow.handler = hub_entry.entry_id
    else:
        flow.handler = DOMAIN
    step_id = flow.init_step if isinstance(flow, OptionsFlow) else SOURCE_USER

    result = await getattr(flow, f"async_step_{step_id}")(None)

    labels = set(form_labels(result["data_schema"]))
    descriptions = {(*path[:-2], "data_description", path[-1]) for path in labels if path[-2] == "data"}
    translated = _leaf_paths(translation((*prefix, "step", result["step_id"]))) - {("title",), ("description",)}
    assert {
        "missing": sorted(".".join(path) for path in labels - translated),
        "unused": sorted(".".join(path) for path in translated - labels - descriptions),
    } == {"missing": [], "unused": []}
