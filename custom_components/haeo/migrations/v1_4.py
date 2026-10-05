"""Migration helpers for config entry version 1.4 (junction-only nodes)."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.schema.elements import node
from custom_components.haeo.core.schema.migrations.v1_4 import (
    NODE_ROLE_FIELDS,
    NODE_SECTION_ROLE,
    migrate_element_config,
)

_LOGGER = logging.getLogger(__name__)

MINOR_VERSION = 4


def _has_active_role(role: Mapping[str, Any]) -> bool:
    """Return whether a node role enables source or sink behavior.

    Role values are plain booleans as written by the node flow, or constant
    schema values as written by the role switch entities.
    """
    for field in NODE_ROLE_FIELDS:
        value = role.get(field)
        if isinstance(value, Mapping):
            value = value.get("value")
        if value:
            return True
    return False


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate existing config entries to version 1.4.

    Removes the source/sink role from every node subentry, along with the
    switch entities that exposed those role fields.
    """
    if entry.minor_version >= MINOR_VERSION:
        return True

    _LOGGER.info(
        "Migrating %s entry %s to version 1.%s",
        DOMAIN,
        entry.entry_id,
        MINOR_VERSION,
    )

    registry = er.async_get(hass)
    for subentry in list(entry.subentries.values()):
        if subentry.subentry_type != node.ELEMENT_TYPE:
            continue

        if _has_active_role(subentry.data.get(NODE_SECTION_ROLE, {})):
            _LOGGER.warning(
                "Node %s was configured as a power source or sink; "
                "nodes are now always pure junctions, so this role has been removed",
                subentry.title,
            )
        hass.config_entries.async_update_subentry(entry, subentry, data=migrate_element_config(subentry.data))

        for field in NODE_ROLE_FIELDS:
            unique_id = f"{entry.entry_id}_{subentry.subentry_id}_{field}"
            entity_id = registry.async_get_entity_id("switch", DOMAIN, unique_id)
            if entity_id is not None:
                registry.async_remove(entity_id)

    hass.config_entries.async_update_entry(entry, minor_version=MINOR_VERSION)
    _LOGGER.info("Migration complete for %s entry %s", DOMAIN, entry.entry_id)
    return True
