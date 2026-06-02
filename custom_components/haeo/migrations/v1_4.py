"""Migration helpers for config entry version 1.4 (horizon choose selector)."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.schema.migrations.v1_4 import migrate_hub_config

_LOGGER = logging.getLogger(__name__)

MINOR_VERSION = 4


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate existing config entries to version 1.4."""
    _ = hass
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
    _LOGGER.info("Migration complete for %s entry %s", DOMAIN, entry.entry_id)
    return True
