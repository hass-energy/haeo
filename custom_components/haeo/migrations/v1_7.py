"""Migration for config entry version 1.7.

Moves every connection's power limit, price, and efficiency into its ordered
list of segments, through the pure transformation in the core schema migrations.
Each one's input entity keeps its entity ID and history as its segment's entity,
and the entity of one left unset, which becomes no segment, is removed.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema.elements.connection import CONF_SEGMENTS
from custom_components.haeo.core.schema.migrations import v1_7
from custom_components.haeo.core.schema.migrations.v1_7 import MINOR_VERSION
from custom_components.haeo.unique_id import element_unique_id, parse_element_unique_id

__all__ = ["MINOR_VERSION", "async_migrate_entry"]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Give every connection its segments in place of its limit, price, and efficiency sections."""
    # Old input entity key, by subentry, to its segment's key, or None when it becomes no segment
    rekeyed: dict[str, dict[str, str | None]] = {}
    for subentry in list(entry.subentries.values()):
        config = {CONF_ELEMENT_TYPE: subentry.subentry_type, **subentry.data}
        migrated = v1_7.migrate_element_config(config)
        if migrated is None:
            continue
        keys: dict[str, str | None] = {}
        for section, field, _segment_type, _segment_field in v1_7.SEGMENTS_FROM_SECTIONS:
            keys[field] = keys[f"{section}.{field}"] = None
        for index, (section, field, segment_field) in enumerate(v1_7.segment_sources(config)):
            keys[field] = keys[f"{section}.{field}"] = f"{CONF_SEGMENTS}.{index}.{segment_field}"
        rekeyed[subentry.subentry_id] = keys
        hass.config_entries.async_update_subentry(entry, subentry, data=migrated)

    registry = er.async_get(hass)
    for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        parsed = parse_element_unique_id(entry.entry_id, entity_entry.unique_id)
        keys = rekeyed.get(parsed.subentry_id, {}) if parsed is not None else {}
        if parsed is None or parsed.key not in keys:
            continue
        new_key = keys[parsed.key]
        if new_key is None:
            registry.async_remove(entity_entry.entity_id)
        else:
            new_unique_id = element_unique_id(entry.entry_id, parsed.subentry_id, new_key)
            registry.async_update_entity(entity_entry.entity_id, new_unique_id=new_unique_id)

    hass.config_entries.async_update_entry(entry, minor_version=MINOR_VERSION)
    return True
