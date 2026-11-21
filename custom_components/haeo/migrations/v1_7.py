"""Migration for config entry version 1.7.

Moves every connection's power limit, price, and efficiency into its ordered
list of segments, through the pure transformation in the core schema migrations.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema.migrations import v1_7
from custom_components.haeo.core.schema.migrations.v1_7 import MINOR_VERSION

__all__ = ["MINOR_VERSION", "async_migrate_entry"]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Give every connection its segments in place of its limit, price, and efficiency sections."""
    for subentry in list(entry.subentries.values()):
        migrated = v1_7.migrate_element_config({CONF_ELEMENT_TYPE: subentry.subentry_type, **subentry.data})
        if migrated is not None:
            hass.config_entries.async_update_subentry(entry, subentry, data=migrated)

    hass.config_entries.async_update_entry(entry, minor_version=MINOR_VERSION)
    return True
