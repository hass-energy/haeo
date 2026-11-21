"""The selector behind the buffer form's preview.

Home Assistant renders a selector of type ``haeo_buffer_preview`` as the
``ha-selector-haeo_buffer_preview`` element from HAEO's selector bundle. It sets
no value: it plans with the buffer as the rest of the form has it, through the
``haeo/buffer_preview`` command, and charts the buffer's line and the charge the
batteries would follow, beside the hub's plan now.
"""

from collections.abc import Iterator
from typing import TypedDict

from homeassistant.helpers.selector import Selector
import voluptuous as vol

BUFFER_PREVIEW_SELECTOR_TYPE = "haeo_buffer_preview"

# Translation key of the element's labels, under selector.<key>.options
BUFFER_PREVIEW_TRANSLATION_KEY = "buffer_preview"

# The chart's legend, and its accessible summary for each kind of buffer
BUFFER_PREVIEW_STRINGS: dict[str, tuple[str, ...]] = {
    "buffer": (),
    "now": (),
    "with_buffer": (),
    "summary_reserve": ("held", "plan", "now"),
    "summary_headroom": ("held", "plan", "now"),
}


class BufferPreviewSelectorConfig(TypedDict):
    """The hub to plan on, and the buffer the form reconfigures, if any."""

    entry_id: str
    replaces: str | None


class BufferPreviewSelector(Selector[BufferPreviewSelectorConfig]):
    """Show what the buffer being configured would do; it holds no value."""

    selector_type = BUFFER_PREVIEW_SELECTOR_TYPE

    CONFIG_SCHEMA = vol.Schema({vol.Required("entry_id"): str, vol.Required("replaces"): vol.Any(None, str)})

    def __call__(self, data: object) -> None:
        """Accept whatever the form submits for the preview, which holds nothing."""
        _ = data

    @staticmethod
    def translation_strings() -> Iterator[tuple[tuple[str, ...], tuple[str, ...]]]:
        """Yield the path of every label the element shows, with the placeholders it fills in."""
        for key, placeholders in BUFFER_PREVIEW_STRINGS.items():
            yield ("selector", BUFFER_PREVIEW_TRANSLATION_KEY, "options", key), placeholders


__all__ = [
    "BUFFER_PREVIEW_SELECTOR_TYPE",
    "BUFFER_PREVIEW_STRINGS",
    "BUFFER_PREVIEW_TRANSLATION_KEY",
    "BufferPreviewSelector",
    "BufferPreviewSelectorConfig",
]
