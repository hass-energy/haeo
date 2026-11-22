"""Tests for the selector behind the buffer form's preview."""

import pytest
import voluptuous as vol

from custom_components.haeo.flows.buffer_preview_selector import BufferPreviewSelector


@pytest.mark.parametrize("submitted", [None, {}, "anything"])
def test_preview_holds_no_value(submitted: object) -> None:
    """Whatever the form submits for the preview, it holds nothing."""
    selector = BufferPreviewSelector({"entry_id": "hub", "replaces": None})

    assert selector(submitted) is None


def test_preview_needs_the_hub_and_the_buffer_it_replaces() -> None:
    """The config names the hub to plan on and the buffer being reconfigured, if any."""
    with pytest.raises(vol.Invalid):
        BufferPreviewSelector({"entry_id": "hub"})
