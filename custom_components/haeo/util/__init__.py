"""Utility functions for HAEO."""

from collections.abc import Callable
import copy
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import ELEMENT_TYPE_NETWORK
from custom_components.haeo.core.schema.elements import map_element_references
from custom_components.haeo.elements import InputFieldPath, set_nested_config_value_by_path

if TYPE_CHECKING:
    from custom_components.haeo import HaeoConfigEntry


def network_subentry(entry: ConfigEntry) -> ConfigSubentry:
    """Return the hub's network subentry, which setup creates before anything reads it.

    Raises:
        StopIteration: When the hub has no network subentry.

    """
    return next(subentry for subentry in entry.subentries.values() if subentry.subentry_type == ELEMENT_TYPE_NETWORK)


def update_element_references(hass: HomeAssistant, entry: ConfigEntry, resolve: Callable[[str], str | None]) -> None:
    """Replace each element name every element's config holds with what resolve returns for it.

    Names resolve returns None for are dropped where an element lists them,
    and an element left with nothing to do is removed. Each write fires the
    update listener eagerly, which may update references itself, so every
    subentry is read afresh and one already removed is skipped.
    """
    for subentry_id in list(entry.subentries):
        if (subentry := entry.subentries.get(subentry_id)) is None:
            continue
        mapped = map_element_references(subentry.subentry_type, subentry.data, resolve)
        if mapped is None:
            hass.config_entries.async_remove_subentry(entry, subentry.subentry_id)
        elif mapped != subentry.data:
            hass.config_entries.async_update_subentry(entry, subentry, data=mapped)


async def async_update_subentry_value(
    hass: HomeAssistant,
    entry: "HaeoConfigEntry",
    subentry: ConfigSubentry,
    field_path: InputFieldPath,
    value: object,
) -> None:
    """Update a single field value in a subentry without triggering reload.

    When the value changes, this function sets a flag on runtime_data before
    updating the subentry, which signals async_update_listener to skip the full
    integration reload and just refresh the coordinator instead. Writing the
    value the field already has does nothing.

    Args:
        hass: Home Assistant instance.
        entry: The hub config entry.
        subentry: The subentry to update.
        field_path: Path to the field to update.
        value: New value for the field.

    """
    new_data = copy.deepcopy(dict(subentry.data))
    set_nested_config_value_by_path(new_data, field_path, value)
    # An unchanged subentry fires no update listener, which is what clears the flag
    if new_data == dict(subentry.data):
        return

    # Set flag to prevent reload
    runtime_data = entry.runtime_data
    if runtime_data is not None:
        runtime_data.value_update_in_progress = True

    try:
        hass.config_entries.async_update_subentry(
            entry,
            subentry,
            data=new_data,
        )
    except Exception:
        if runtime_data is not None:
            runtime_data.value_update_in_progress = False
        raise


__all__ = [
    "async_update_subentry_value",
    "update_element_references",
]
