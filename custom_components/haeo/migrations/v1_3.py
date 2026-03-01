"""Migration helpers for config entry version 1.3."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.schema.migrations.v1_3 import migrate_element_config, migrate_hub_config

_LOGGER = logging.getLogger(__name__)

MINOR_VERSION = 3


def migrate_subentry_data(subentry: ConfigSubentry) -> dict[str, Any] | None:
    """Migrate a subentry's data to sectioned config if needed."""
    return migrate_element_config(dict(subentry.data))


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate existing config entries to version 1.3."""
    if entry.minor_version >= MINOR_VERSION:
        return True

    _LOGGER.info(
        "Migrating %s entry %s to version 1.%s",
        DOMAIN,
        entry.entry_id,
        MINOR_VERSION,
    )

    new_data, new_options = migrate_hub_config(dict(entry.data), dict(entry.options), entry.title)
    hass.config_entries.async_update_entry(
        entry,
        data=new_data,
        options=new_options,
        minor_version=MINOR_VERSION,
    )

    for subentry in entry.subentries.values():
        migrated = migrate_subentry_data(subentry)
        if migrated is not None:
            hass.config_entries.async_update_subentry(entry, subentry, data=migrated)

    _LOGGER.info("Migration complete for %s entry %s", DOMAIN, entry.entry_id)
    return True
