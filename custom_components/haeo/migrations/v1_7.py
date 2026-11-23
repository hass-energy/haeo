"""Migration for config entry version 1.7.

Names each buffer's loads and generation by one of their sensors, through the
pure transformation in the core schema migrations. An element's sensor is its
main power output, or another of its entities when it has none. An element
with no registered entity stays named directly.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema.migrations import v1_7
from custom_components.haeo.core.schema.migrations.v1_7 import MINOR_VERSION
from custom_components.haeo.elements import element_sensors

__all__ = ["MINOR_VERSION", "async_migrate_entry"]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Name every buffer's loads and generation by their sensors."""
    sensors = element_sensors(hass, entry)
    for subentry in list(entry.subentries.values()):
        migrated = v1_7.migrate_element_config({CONF_ELEMENT_TYPE: subentry.subentry_type, **subentry.data}, sensors)
        if migrated is not None:
            hass.config_entries.async_update_subentry(entry, subentry, data=migrated)

    hass.config_entries.async_update_entry(entry, minor_version=MINOR_VERSION)
    return True
