"""Migration for config entry version 1.6.

Gives every EV saved without a public charging price the default, through the
pure transformation in the core schema migrations.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema.migrations import v1_6
from custom_components.haeo.core.schema.migrations.v1_6 import MINOR_VERSION

__all__ = ["MINOR_VERSION", "async_migrate_entry"]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set the default public charging price on every EV saved without one."""
    for subentry in list(entry.subentries.values()):
        migrated = v1_6.migrate_element_config({CONF_ELEMENT_TYPE: subentry.subentry_type, **subentry.data})
        if migrated is not None:
            hass.config_entries.async_update_subentry(entry, subentry, data=migrated)

    hass.config_entries.async_update_entry(entry, minor_version=MINOR_VERSION)
    return True
