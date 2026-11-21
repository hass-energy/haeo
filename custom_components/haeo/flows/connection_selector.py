"""The selector behind an element's connection field.

Home Assistant renders a selector of type ``haeo_connection`` as the
``ha-selector-haeo_connection`` element from HAEO's selector bundle. The
element shows each element the new one can connect to as a bus, AC or DC, with
the elements already connected to it, and reports the chosen element's name.
"""

from collections.abc import Iterator
from typing import TypedDict

from homeassistant.helpers.selector import Selector
import voluptuous as vol

CONNECTION_SELECTOR_TYPE = "haeo_connection"

# Translation key of the element's labels, under selector.<key>.options
CONNECTION_TRANSLATION_KEY = "connection"

# The element's accessible labels, with the placeholders the element fills in
CONNECTION_STRINGS: dict[str, tuple[str, ...]] = {
    "ac_bus": ("name",),
    "dc_bus": ("name",),
}


class ConnectedElement(TypedDict):
    """An element already connected to a target."""

    name: str
    element_type: str


class ConnectionTarget(TypedDict):
    """An element the field can connect to, and what is already connected to it."""

    name: str
    element_type: str
    dc: bool
    elements: list[ConnectedElement]


class ConnectionSelectorConfig(TypedDict):
    """What the connection element offers, for an element of ``element_type``."""

    element_type: str
    targets: list[ConnectionTarget]


_ELEMENT = vol.Schema({vol.Required("name"): str, vol.Required("element_type"): str})


class ConnectionSelector(Selector[ConnectionSelectorConfig]):
    """Select the element an element connects to."""

    selector_type = CONNECTION_SELECTOR_TYPE

    CONFIG_SCHEMA = vol.Schema(
        {
            vol.Required("element_type"): str,
            vol.Required("targets"): [
                vol.Schema(
                    {
                        vol.Required("name"): str,
                        vol.Required("element_type"): str,
                        vol.Required("dc"): bool,
                        vol.Required("elements"): [_ELEMENT],
                    }
                )
            ],
        }
    )

    def __call__(self, data: object) -> str:
        """Validate the chosen element's name."""
        names = [target["name"] for target in self.config["targets"]]
        return vol.In(names)(data)

    @staticmethod
    def translation_strings() -> Iterator[tuple[tuple[str, ...], tuple[str, ...]]]:
        """Yield the path of every label the element gives its controls, with the placeholders it fills in."""
        for key, placeholders in CONNECTION_STRINGS.items():
            yield ("selector", CONNECTION_TRANSLATION_KEY, "options", key), placeholders


__all__ = [
    "CONNECTION_SELECTOR_TYPE",
    "CONNECTION_STRINGS",
    "CONNECTION_TRANSLATION_KEY",
    "ConnectedElement",
    "ConnectionSelector",
    "ConnectionSelectorConfig",
    "ConnectionTarget",
]
