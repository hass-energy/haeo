"""Migration helpers for config entry version 1.5.

Migrates entity unique_ids from section-path format to stable field-name
format. Prior to this migration, unique_ids included the full config section
path (e.g. ``storage.capacity``). After migration, simple fields use just
the field name (``capacity``), making them stable across config restructuring.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)

MINOR_VERSION = 5


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate entity unique_ids to field-name-only format."""
    if entry.minor_version >= MINOR_VERSION:
        return True

    def _migrate_unique_id(entity_entry: er.RegistryEntry) -> dict[str, Any] | None:
        uid = entity_entry.unique_id
        if not uid:
            return None

        # Format: {entry_id}_{subentry_id}_{field_path_key}
        # We want to change section.field_name to just field_name
        # for simple (non-list) fields.
        parts = uid.split("_", 2)  # entry_id, subentry_id, field_path_key
        if len(parts) != 3:  # noqa: PLR2004
            return None

        field_path_key = parts[2]
        path_parts = field_path_key.split(".")

        # List items (e.g. rules.0.price) — keep as-is
        if len(path_parts) > 2:  # noqa: PLR2004
            return None

        # Simple fields with section prefix (e.g. storage.capacity) — strip section
        if len(path_parts) == 2:  # noqa: PLR2004
            new_key = path_parts[1]
            new_uid = f"{parts[0]}_{parts[1]}_{new_key}"
            _LOGGER.debug("Migrating entity unique_id: %s -> %s", uid, new_uid)
            return {"new_unique_id": new_uid}

        # Already just a field name — no change needed
        return None

    await er.async_migrate_entries(hass, entry.entry_id, _migrate_unique_id)

    hass.config_entries.async_update_entry(
        entry,
        minor_version=MINOR_VERSION,
    )
    _LOGGER.info("Migrated entity unique_ids to v1.%d", MINOR_VERSION)
    return True
