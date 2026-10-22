"""Migration for config entry version 1.5.

Removes the number entities of inputs that are now switches, such as whether
an EV is plugged in and the availability read from calendars, so they do not
linger beside the switches that replace them.
"""

from __future__ import annotations

from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.elements import get_input_fields, iter_input_field_paths
from custom_components.haeo.elements.input_fields import is_switch_field_info
from custom_components.haeo.unique_id import parse_element_unique_id

MINOR_VERSION: Final = 5


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove the number entities of inputs that are now switches."""
    if entry.minor_version >= MINOR_VERSION:
        return True

    # An input's entity is keyed by its field name, or by its section and field
    # name when another section reuses the name, so both are matched
    switch_keys = {
        subentry.subentry_id: {
            key
            for path, field_info in iter_input_field_paths(get_input_fields(ElementType(subentry.subentry_type)))
            if is_switch_field_info(field_info)
            for key in (path[-1], ".".join(path))
        }
        for subentry in entry.subentries.values()
        if subentry.subentry_type in ELEMENT_TYPES
    }

    registry = er.async_get(hass)
    for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity_entry.domain != "number" or entity_entry.platform != DOMAIN:
            continue
        parsed = parse_element_unique_id(entry.entry_id, entity_entry.unique_id)
        if parsed is not None and parsed.key in switch_keys.get(parsed.subentry_id, ()):
            registry.async_remove(entity_entry.entity_id)

    hass.config_entries.async_update_entry(entry, minor_version=MINOR_VERSION)
    return True
