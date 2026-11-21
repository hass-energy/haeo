"""The selector behind every HAEO input field.

Home Assistant renders a selector of type ``haeo_input`` as the
``ha-selector-haeo_input`` element from HAEO's selector bundle. The element
shows the field's value directly (nothing, a fixed value, or a list of
entities) and reports it in the same discriminated form HAEO stores, so the
flow saves what it receives.
"""

from collections.abc import Iterator, Mapping
from typing import Literal, NotRequired, TypedDict

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import Selector
import voluptuous as vol

from custom_components.haeo.core.schema import (
    VALUE_TYPE_CONSTANT,
    VALUE_TYPE_ENTITY,
    VALUE_TYPE_NONE,
    SchemaValue,
    as_constant_value,
    as_entity_value,
    as_none_value,
)

INPUT_SELECTOR_TYPE = "haeo_input"

# Translation key of the element's own text, under selector.<key>.options
INPUT_TRANSLATION_KEY = "input"
# Each string the element shows, with the placeholders the element fills in
INPUT_STRINGS: dict[str, tuple[str, ...]] = {
    "add_all": ("count",),
    "clear": (),
    "fixed_off": (),
    "fixed_on": (),
    "fixed_value": (),
    "hint_add_all": (),
    "hint_value": (),
    "no_matches": (),
    "not_set": (),
    "off": (),
    "on": (),
    "remove": ("name",),
    "search": (),
    "search_or_value": (),
    "selected": ("label",),
    "use_value": ("value",),
}

type InputKind = Literal["entity", "constant", "none"]


class InputSelectorConfig(TypedDict):
    """What the input element offers."""

    kinds: list[InputKind]
    value_type: Literal["number", "boolean"]
    multiple: bool
    entities: list[str]
    min: NotRequired[float]
    max: NotRequired[float]
    step: NotRequired[float]
    unit: NotRequired[str]


class InputSelector(Selector[InputSelectorConfig]):
    """Select an input's value: nothing, a fixed value, or entities."""

    selector_type = INPUT_SELECTOR_TYPE

    CONFIG_SCHEMA = vol.Schema(
        {
            vol.Required("kinds"): [vol.In([VALUE_TYPE_ENTITY, VALUE_TYPE_CONSTANT, VALUE_TYPE_NONE])],
            vol.Required("value_type"): vol.In(["number", "boolean"]),
            vol.Required("multiple"): bool,
            vol.Required("entities"): [str],
            vol.Optional("min"): vol.Coerce(float),
            vol.Optional("max"): vol.Coerce(float),
            vol.Optional("step"): vol.Coerce(float),
            vol.Optional("unit"): str,
        }
    )

    def __call__(self, data: object) -> SchemaValue:
        """Validate a submitted value.

        An empty entity list reads as no value. Whether a field may be left
        without a value is the flow's to check, so it can name the section the
        field is in.
        """
        if not isinstance(data, Mapping):
            msg = "Expected an input value"
            raise vol.Invalid(msg)
        match data.get("type"):
            case "none":
                return as_none_value()
            case "entity" if VALUE_TYPE_ENTITY in self.config["kinds"]:
                value = data.get("value")
                entity_ids = cv.entity_ids(value) if isinstance(value, str | list) else []
                if not entity_ids:
                    return as_none_value()
                if not self.config["multiple"] and len(entity_ids) > 1:
                    msg = "Only one entity is allowed"
                    raise vol.Invalid(msg)
                return as_entity_value(
                    entity_ids,
                    on_states=self._states(data.get("on_states")),
                    off_states=self._states(data.get("off_states")),
                )
            case "constant" if VALUE_TYPE_CONSTANT in self.config["kinds"]:
                return as_constant_value(self._constant(data.get("value")))
            case _:
                msg = "Unsupported input value"
                raise vol.Invalid(msg)

    @staticmethod
    def _states(value: object) -> list[str]:
        """Return the states an entity value lists as on or off, which the element passes through."""
        return [str(state) for state in value] if isinstance(value, list | tuple) else []

    def _constant(self, value: object) -> float | bool:
        if self.config["value_type"] == "boolean":
            return cv.boolean(value)
        number = vol.Coerce(float)(value)
        return vol.Range(min=self.config.get("min"), max=self.config.get("max"))(number)

    @staticmethod
    def translation_strings() -> Iterator[tuple[tuple[str, ...], tuple[str, ...]]]:
        """Yield the path of every string the element shows, with the placeholders it fills in."""
        for key, placeholders in INPUT_STRINGS.items():
            yield ("selector", INPUT_TRANSLATION_KEY, "options", key), placeholders


__all__ = ["INPUT_SELECTOR_TYPE", "INPUT_STRINGS", "INPUT_TRANSLATION_KEY", "InputSelector", "InputSelectorConfig"]
