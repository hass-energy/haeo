"""The selector behind a connection element's path.

Home Assistant renders a selector of type ``haeo_connection_path`` as the
``ha-selector-haeo_connection_path`` element from HAEO's selector bundle. The
element shows the connection as a chain from its source, through each segment in
the order power passes through it, to its target. Each segment edits its one
input with the input element, and segments are added, moved, and removed in place.
"""

from collections.abc import Iterator, Mapping
from typing import TypedDict

from homeassistant.helpers.selector import Selector
import voluptuous as vol

from custom_components.haeo.core.schema.elements.connection import (
    CONF_SEGMENT_TYPE,
    CONF_SEGMENTS,
    CONF_SOURCE,
    CONF_TARGET,
    SEGMENT_FIELDS,
)
from custom_components.haeo.flows.connection_selector import ConnectedElement
from custom_components.haeo.flows.input_selector import InputSelector, InputSelectorConfig

CONNECTION_PATH_SELECTOR_TYPE = "haeo_connection_path"

# Translation key of the element's labels, under selector.<key>.options
CONNECTION_PATH_TRANSLATION_KEY = "connection_path"

# The element's text: each segment type's name, and accessible labels, with the placeholders the element fills in
CONNECTION_PATH_STRINGS: dict[str, tuple[str, ...]] = {
    "add_segment": (),
    "cancel": (),
    "efficiency": (),
    "move_earlier": ("segment",),
    "move_later": ("segment",),
    "power_limit": (),
    "pricing": (),
    "remove_segment": ("segment",),
    "source": (),
    "target": (),
}


class SegmentTypeConfig(TypedDict):
    """How the element edits one kind of segment: the field it sets, through an input element."""

    field: str
    input: InputSelectorConfig


class ConnectionPathSelectorConfig(TypedDict):
    """What the path element offers: the elements to connect, and the kinds of segment."""

    participants: list[ConnectedElement]
    segment_types: dict[str, SegmentTypeConfig]


class ConnectionPath(TypedDict):
    """A connection's source, target, and segments, as the element reports them."""

    source: str
    target: str
    segments: list[dict[str, object]]


class ConnectionPathSelector(Selector[ConnectionPathSelectorConfig]):
    """Select a connection's endpoints and the segments between them."""

    selector_type = CONNECTION_PATH_SELECTOR_TYPE

    CONFIG_SCHEMA = vol.Schema(
        {
            vol.Required("participants"): [vol.Schema({vol.Required("name"): str, vol.Required("element_type"): str})],
            vol.Required("segment_types"): {
                vol.In(list(SEGMENT_FIELDS)): {vol.Required("field"): str, vol.Required("input"): dict}
            },
        }
    )

    def __call__(self, data: object) -> ConnectionPath:
        """Validate the endpoints and each segment's input."""
        if not isinstance(data, Mapping):
            msg = "Expected a connection path"
            raise vol.Invalid(msg)
        names = vol.In([participant["name"] for participant in self.config["participants"]])
        segments = data.get(CONF_SEGMENTS, [])
        if not isinstance(segments, list):
            msg = "Expected a list of segments"
            raise vol.Invalid(msg)
        return {
            "source": names(data.get(CONF_SOURCE)),
            "target": names(data.get(CONF_TARGET)),
            "segments": [self._segment(segment) for segment in segments],
        }

    def _segment(self, segment: object) -> dict[str, object]:
        """Validate one segment's type and its input."""
        if not isinstance(segment, Mapping):
            msg = "Expected a segment"
            raise vol.Invalid(msg)
        segment_type = vol.In(list(self.config["segment_types"]))(segment.get(CONF_SEGMENT_TYPE))
        kind = self.config["segment_types"][segment_type]
        field = kind["field"]
        return {
            CONF_SEGMENT_TYPE: segment_type,
            field: InputSelector(kind["input"])(segment.get(field, {"type": "none"})),
        }

    @staticmethod
    def translation_strings() -> Iterator[tuple[tuple[str, ...], tuple[str, ...]]]:
        """Yield the path of every label the element gives its controls, with the placeholders it fills in."""
        for key, placeholders in CONNECTION_PATH_STRINGS.items():
            yield ("selector", CONNECTION_PATH_TRANSLATION_KEY, "options", key), placeholders


__all__ = [
    "CONNECTION_PATH_SELECTOR_TYPE",
    "CONNECTION_PATH_STRINGS",
    "CONNECTION_PATH_TRANSLATION_KEY",
    "ConnectionPath",
    "ConnectionPathSelector",
    "ConnectionPathSelectorConfig",
    "SegmentTypeConfig",
]
