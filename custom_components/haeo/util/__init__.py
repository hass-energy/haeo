"""Utility functions for HAEO."""

import copy
from functools import reduce
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.util.hass_dict import HassKey

from custom_components.haeo.const import DOMAIN, ELEMENT_TYPE_NETWORK
from custom_components.haeo.core.schema.elements import ElementType, map_element_references, referenced_element_names
from custom_components.haeo.core.schema.elements.policy import CONF_RULES
from custom_components.haeo.core.schema.surfaced_policy import without_owned_rules
from custom_components.haeo.elements import InputFieldPath, set_nested_config_value_by_path

if TYPE_CHECKING:
    from custom_components.haeo import HaeoConfigEntry


def network_subentry(entry: ConfigEntry) -> ConfigSubentry:
    """Return the hub's network subentry, which setup creates before anything reads it.

    Raises:
        StopIteration: When the hub has no network subentry.

    """
    return next(subentry for subentry in entry.subentries.values() if subentry.subentry_type == ELEMENT_TYPE_NETWORK)


def rename_element_references(hass: HomeAssistant, entry: ConfigEntry, old_name: str, new_name: str) -> None:
    """Rename an element in the config of every element that names it, and in the elements remembered for the entry.

    Only elements that name it are rewritten.
    """
    for subentry in list(entry.subentries.values()):
        if old_name in referenced_element_names(subentry.subentry_type, subentry.data):
            mapped = map_element_references(
                subentry.subentry_type, subentry.data, lambda name: new_name if name == old_name else name
            )
            hass.config_entries.async_update_subentry(entry, subentry, data=mapped)
    # The element may be deleted before the update listener next runs, such as
    # while setup waits to retry, and must then be found under its new name
    known = hass.data.get(KNOWN_ELEMENTS, {}).get(entry.entry_id, {})
    for subentry_id, (element_type, name) in known.items():
        if name == old_name:
            known[subentry_id] = (element_type, new_name)


# The type and name of each element of an entry, by entry ID and then subentry ID,
# as they were when its config last changed
KNOWN_ELEMENTS: HassKey[dict[str, dict[str, tuple[str, str]]]] = HassKey(f"{DOMAIN}_known_elements")


def remove_deleted_elements_rules(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the policy rules that each element deleted since the last call surfaced on its own form.

    Elements are remembered by subentry ID, so a rename never counts as a
    deletion, and the first call for an entry only remembers its elements.
    An element whose name another element has taken since keeps its rules,
    as they are now that element's. Every other reference to a deleted
    element stays for setup to report.
    """
    known = hass.data.setdefault(KNOWN_ELEMENTS, {})
    previous = known.get(entry.entry_id, {})
    # Remember the elements before writing, as the write runs the update listener again
    known[entry.entry_id] = {
        subentry_id: (subentry.subentry_type, subentry.title) for subentry_id, subentry in entry.subentries.items()
    }
    names = {subentry.title for subentry in entry.subentries.values()}
    deleted = [
        (element_type, name)
        for subentry_id, (element_type, name) in previous.items()
        if subentry_id not in entry.subentries and name not in names
    ]
    policies = [subentry for subentry in entry.subentries.values() if subentry.subentry_type == ElementType.POLICY]
    for policy in policies:
        rules = policy.data[CONF_RULES]
        kept = reduce(lambda kept, element: without_owned_rules(kept, *element), deleted, list(rules))
        if kept != rules:
            hass.config_entries.async_update_subentry(entry, policy, data={**policy.data, CONF_RULES: kept})


def forget_elements(hass: HomeAssistant, entry_id: str) -> None:
    """Forget the elements remembered for a removed entry."""
    hass.data.get(KNOWN_ELEMENTS, {}).pop(entry_id, None)


def missing_element_references(entry: ConfigEntry) -> dict[str, list[str]]:
    """Return the names each element refers to that no element of the entry has, by element."""
    names = {subentry.title for subentry in entry.subentries.values()}
    missing = {
        subentry.title: sorted(referenced_element_names(subentry.subentry_type, subentry.data) - names)
        for subentry in entry.subentries.values()
    }
    return {element: absent for element, absent in missing.items() if absent}


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
    "KNOWN_ELEMENTS",
    "async_update_subentry_value",
    "forget_elements",
    "missing_element_references",
    "remove_deleted_elements_rules",
    "rename_element_references",
]
