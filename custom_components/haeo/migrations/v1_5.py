"""Migration helpers for config entry version 1.5.

Links each element entity to its element's subentry, so Home Assistant removes
the entities along with the element, and removes the entities of elements that
were deleted before entities were linked.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.haeo.const import DOMAIN

_LOGGER = logging.getLogger(__name__)

MINOR_VERSION = 5

# Unique ID suffixes of the hub's own entities. Every setup adds these linked to
# the network subentry, so they need no migration.
_HUB_ENTITY_KEYS: frozenset[str] = frozenset({"auto_optimize", "horizon"})


def _link_entities_to_subentries(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Link unlinked element entities to their subentry, or remove them if it no longer exists.

    Element entity unique IDs are ``{entry_id}_{subentry_id}_{key}``.
    """
    registry = er.async_get(hass)
    prefix = f"{entry.entry_id}_"
    for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity_entry.config_subentry_id is not None:
            continue
        key = entity_entry.unique_id.removeprefix(prefix)
        if key in _HUB_ENTITY_KEYS:
            continue
        subentry_id = key.split("_", 1)[0]
        if subentry_id in entry.subentries:
            registry.async_update_entity(entity_entry.entity_id, config_subentry_id=subentry_id)
        else:
            _LOGGER.info("Removing %s because its element no longer exists", entity_entry.entity_id)
            registry.async_remove(entity_entry.entity_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate existing config entries to version 1.5."""
    if entry.minor_version >= MINOR_VERSION:
        return True

    _LOGGER.info("Migrating %s entry %s to version 1.%s", DOMAIN, entry.entry_id, MINOR_VERSION)

    _link_entities_to_subentries(hass, entry)

    hass.config_entries.async_update_entry(entry, minor_version=MINOR_VERSION)
    _LOGGER.info("Migration complete for %s entry %s", DOMAIN, entry.entry_id)
    return True
