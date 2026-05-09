"""Migration helpers for config entry version 1.4.

Adds a ``threshold`` section with a default ``threshold_price`` of 0 to every
Load subentry. The optimization behaviour is unchanged at price=0; users who
want the load to shed when energy is expensive raise this value.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.schema.migrations.v1_4 import migrate_element_config

_LOGGER = logging.getLogger(__name__)

MINOR_VERSION = 4


def migrate_subentry_data(subentry: ConfigSubentry) -> dict[str, Any] | None:
    """Migrate a subentry's data to add a threshold section to loads if missing."""
    return migrate_element_config(dict(subentry.data))


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate existing config entries to version 1.4."""
    if entry.minor_version >= MINOR_VERSION:
        return True

    _LOGGER.info(
        "Migrating %s entry %s to version 1.%s",
        DOMAIN,
        entry.entry_id,
        MINOR_VERSION,
    )

    for subentry in entry.subentries.values():
        migrated = migrate_subentry_data(subentry)
        if migrated is not None and migrated != dict(subentry.data):
            hass.config_entries.async_update_subentry(entry, subentry, data=migrated)

    hass.config_entries.async_update_entry(entry, minor_version=MINOR_VERSION)
    _LOGGER.info("Migration complete for %s entry %s", DOMAIN, entry.entry_id)
    return True
