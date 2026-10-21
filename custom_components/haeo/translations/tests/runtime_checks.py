"""Pytest plugin that fails a test when HAEO shows a string that en.json does not translate.

Home Assistant core runs every test under a ``check_translations`` fixture, but
pytest-homeassistant-custom-component does not ship it, and core's version
skips config subentry flows.
This plugin checks the same things, plus subentry flows, selector options,
entity names, and enum sensor states, as each one is shown during a test:

- Flow forms: section names, field labels, selector options, and errors
- Flow aborts
- Repair issues, and the steps of their fix flows
- Home Assistant errors raised with a HAEO translation key
- Entity names and enum sensor states

Every placeholder a string uses must also be supplied.
"""

from collections.abc import Awaitable, Callable, Generator, Iterator, Mapping
from functools import cache
import json
from pathlib import Path
import string

from homeassistant.components.repairs import RepairsFlow
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigSubentryFlow, OptionsFlow
from homeassistant.data_entry_flow import FlowHandler, FlowResult, section
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.selector import ChooseSelector, Selector, SelectSelector
import pytest
import voluptuous as vol

from custom_components.haeo.const import DOMAIN

TRANSLATIONS_PATH = Path(__file__).parent.parent / "en.json"

type TranslationPath = tuple[str, ...]


@cache
def load_translations() -> Mapping[str, object]:
    """Return the parsed en.json."""
    with TRANSLATIONS_PATH.open() as file:
        return json.load(file)


def translation(path: TranslationPath) -> object | None:
    """Return the value at a path through en.json, or None when there is none."""
    node: object = load_translations()
    for key in path:
        if not isinstance(node, Mapping) or key not in node:
            return None
        node = node[key]
    return node


class TranslationChecker:
    """Collect the problems with strings shown during one test."""

    def __init__(self) -> None:
        """Start with no problems."""
        self.problems: list[str] = []

    def require(self, path: TranslationPath, placeholders: Mapping[str, str] | None = None) -> None:
        """Record a problem unless path names a string whose placeholders are all supplied."""
        text = translation(path)
        if not isinstance(text, str):
            self.problems.append(f"Missing translation {'.'.join(path)}")
            return
        self.check_placeholders(path, text, placeholders)

    def optional(self, path: TranslationPath, placeholders: Mapping[str, str] | None) -> None:
        """Check the placeholders of a string that may be left untranslated."""
        text = translation(path)
        if isinstance(text, str):
            self.check_placeholders(path, text, placeholders)

    def check_placeholders(self, path: TranslationPath, text: str, placeholders: Mapping[str, str] | None) -> None:
        """Record every placeholder the text uses that is not supplied."""
        supplied = placeholders or {}
        self.problems.extend(
            f"{'.'.join(path)} uses placeholder {{{name}}}, which is not supplied"
            for _, name, _, _ in string.Formatter().parse(text)
            if name is not None and name not in supplied
        )

    def check_form(self, prefix: TranslationPath, placeholders: Mapping[str, str], result: FlowResult) -> None:
        """Check the strings a flow form shows."""
        step = (*prefix, "step", str(result.get("step_id")))
        for header in ("title", "description"):
            self.optional((*step, header), placeholders)
        if (schema := result.get("data_schema")) is not None:
            self.check_schema(step, schema)
        for error in (result.get("errors") or {}).values():
            self.require((*prefix, "error", error), placeholders)

    def check_schema(self, step: TranslationPath, schema: vol.Schema) -> None:
        """Check the label of every field and section in a form, and the options of its selectors."""
        for path, validator in form_labels(schema).items():
            self.require((*step, *path))
            if isinstance(validator, Selector):
                for selector_path in selector_translation_paths(validator):
                    self.require(selector_path)

    def check_entity(self, entity: Entity) -> None:
        """Check the name of an entity and, for an enum sensor, the name of every state."""
        if entity.translation_key is None:
            return
        path = ("entity", entity.platform.domain, entity.translation_key)
        self.require((*path, "name"), entity.translation_placeholders)
        if isinstance(entity, SensorEntity) and entity.device_class == SensorDeviceClass.ENUM:
            for option in entity.options or []:
                self.require((*path, "state", option))


def form_labels(schema: vol.Schema) -> dict[TranslationPath, object]:
    """Return the path of the label of every field and section in a form, relative to its step, with its validator."""
    labels: dict[TranslationPath, object] = {}
    for key, validator in schema.schema.items():
        name = str(key.schema) if isinstance(key, vol.Marker) else str(key)
        if isinstance(validator, section):
            labels[("sections", name, "name")] = validator
            labels.update({("sections", name, *path): nested for path, nested in form_labels(validator.schema).items()})
        else:
            labels[("data", name)] = validator
    return labels


def selector_translation_paths(selector: Selector[Mapping[str, object]]) -> Iterator[TranslationPath]:
    """Yield the path of every option label a selector translates."""
    config = selector.config
    key = config.get("translation_key")
    options = config.get("options")
    choices = config.get("choices")
    if isinstance(selector, SelectSelector) and isinstance(key, str) and isinstance(options, list):
        for option in options:
            yield ("selector", key, "options", option if isinstance(option, str) else option["value"])
    if isinstance(selector, ChooseSelector) and isinstance(choices, Mapping):
        for choice_key, choice in choices.items():
            if isinstance(key, str):
                yield ("selector", key, "choices", choice_key)
            if isinstance(nested := choice["selector"], Selector):
                yield from selector_translation_paths(nested)


def flow_strings(
    flow: FlowHandler, placeholders: Mapping[str, str] | None
) -> tuple[TranslationPath, Mapping[str, str]]:
    """Return where a flow's strings live in en.json and the placeholders they may use."""
    supplied: Mapping[str, str] = placeholders or {}
    if isinstance(flow, ConfigSubentryFlow):
        return ("config_subentries", flow.handler[1]), supplied
    if isinstance(flow, OptionsFlow):
        return ("options",), supplied
    if isinstance(flow, RepairsFlow):
        issue = ir.async_get(flow.hass).issues[(DOMAIN, flow.issue_id)]
        return ("issues", str(issue.translation_key), "fix_flow"), {
            **(issue.translation_placeholders or {}),
            **supplied,
        }
    return ("config",), supplied


def is_haeo_flow(flow: FlowHandler) -> bool:
    """Return whether a flow handler belongs to this integration."""
    return type(flow).__module__.startswith(f"custom_components.{DOMAIN}.")


@pytest.fixture(autouse=True)
def check_translations(monkeypatch: pytest.MonkeyPatch) -> Generator[TranslationChecker]:
    """Fail the test when it shows a HAEO string that en.json does not translate."""
    checker = TranslationChecker()

    original_show_form = FlowHandler.async_show_form
    original_abort = FlowHandler.async_abort
    original_issue = ir.IssueRegistry.async_get_or_create
    original_error_init = HomeAssistantError.__init__
    original_added = Entity.async_internal_added_to_hass

    def show_form(self: FlowHandler, **kwargs: object) -> FlowResult:
        result = original_show_form(self, **kwargs)  # type: ignore[arg-type] (keyword arguments pass through unchanged)
        if is_haeo_flow(self):
            checker.check_form(*flow_strings(self, result.get("description_placeholders")), result)
        return result

    def abort(self: FlowHandler, **kwargs: object) -> FlowResult:
        result = original_abort(self, **kwargs)  # type: ignore[arg-type] (keyword arguments pass through unchanged)
        if is_haeo_flow(self):
            prefix, placeholders = flow_strings(self, result.get("description_placeholders"))
            checker.require((*prefix, "abort", str(result.get("reason"))), placeholders)
        return result

    def get_or_create_issue(self: ir.IssueRegistry, domain: str, issue_id: str, **kwargs: object) -> ir.IssueEntry:
        issue = original_issue(self, domain, issue_id, **kwargs)  # type: ignore[arg-type] (keyword arguments pass through unchanged)
        if domain == DOMAIN and issue.translation_key is not None:
            path = ("issues", issue.translation_key)
            checker.require((*path, "title"), issue.translation_placeholders)
            if not issue.is_fixable:
                checker.require((*path, "description"), issue.translation_placeholders)
        return issue

    def error_init(
        self: HomeAssistantError,
        *args: object,
        translation_domain: str | None = None,
        translation_key: str | None = None,
        translation_placeholders: dict[str, str] | None = None,
    ) -> None:
        original_error_init(
            self,
            *args,
            translation_domain=translation_domain,
            translation_key=translation_key,
            translation_placeholders=translation_placeholders,
        )
        if translation_domain == DOMAIN and translation_key is not None:
            checker.require(("exceptions", translation_key, "message"), translation_placeholders)

    def added_to_hass(self: Entity) -> Awaitable[None]:
        if self.platform.platform_name == DOMAIN:
            checker.check_entity(self)
        return original_added(self)

    patches: dict[tuple[type, str], Callable[..., object]] = {
        (FlowHandler, "async_show_form"): show_form,
        (FlowHandler, "async_abort"): abort,
        (ir.IssueRegistry, "async_get_or_create"): get_or_create_issue,
        (HomeAssistantError, "__init__"): error_init,
        (Entity, "async_internal_added_to_hass"): added_to_hass,
    }
    for (owner, name), replacement in patches.items():
        monkeypatch.setattr(owner, name, replacement)

    yield checker

    if checker.problems:
        pytest.fail("Translation problems:\n" + "\n".join(dict.fromkeys(checker.problems)))
