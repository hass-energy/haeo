"""Migration helpers for config entry version 1.4."""

from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import get_connection_target_name
from custom_components.haeo.core.schema.elements import connection
from custom_components.haeo.core.schema.migrations.v1_4 import (
    endpoints_match_reverse,
    merge_reverse_into_existing,
    migrate_connection_config,
)
from custom_components.haeo.core.schema.sections import (
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_TARGET_SOURCE,
)

_LOGGER = logging.getLogger(__name__)

MINOR_VERSION = 4
_CONNECTION_TYPE = connection.ELEMENT_TYPE
_UNIQUE_ID_PART_COUNT = 3

_REVERSE_FIELD_RENAMES: dict[str, str] = {
    CONF_MAX_POWER_TARGET_SOURCE: "max_power_source_target",
    CONF_PRICE_TARGET_SOURCE: "price_source_target",
    CONF_EFFICIENCY_TARGET_SOURCE: "efficiency_source_target",
}


def _collect_subentry_names(entry: ConfigEntry) -> set[str]:
    return {subentry.title for subentry in entry.subentries.values()}


def _find_reverse_subentry(
    entry: ConfigEntry,
    *,
    source_name: str,
    target_name: str,
    exclude_subentry_id: str | None,
) -> ConfigSubentry | None:
    for subentry in entry.subentries.values():
        if subentry.subentry_id == exclude_subentry_id:
            continue
        data = dict(subentry.data)
        if data.get(CONF_ELEMENT_TYPE) != _CONNECTION_TYPE:
            continue
        endpoints = data.get(connection.SECTION_ENDPOINTS, {})
        if not isinstance(endpoints, dict):
            continue
        if endpoints_match_reverse(endpoints, source_name=source_name, target_name=target_name):
            return subentry
    return None


async def _migrate_connection_entity_unique_ids(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    subentry_id_map: dict[str, str],
) -> None:
    """Re-home connection input entities from reverse fields to the new reverse subentry."""
    registry = er.async_get(hass)
    candidate_unique_ids: dict[str, str] = {}
    candidate_counts: dict[str, int] = {}

    for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        uid = entity_entry.unique_id
        if not uid:
            continue

        parts = uid.split("_", 2)
        if len(parts) != _UNIQUE_ID_PART_COUNT:
            continue

        subentry_id = parts[1]
        field_path_key = parts[2]
        new_subentry_id = subentry_id_map.get(subentry_id)
        if new_subentry_id is None:
            continue

        path_parts = field_path_key.split(".")
        leaf = path_parts[-1]
        new_leaf = _REVERSE_FIELD_RENAMES.get(leaf)
        if new_leaf is None:
            continue

        new_uid = f"{parts[0]}_{new_subentry_id}_{new_leaf}"
        if new_uid == uid:
            continue

        candidate_unique_ids[entity_entry.entity_id] = new_uid
        candidate_counts[new_uid] = candidate_counts.get(new_uid, 0) + 1

    def _migrate_unique_id(entity_entry: er.RegistryEntry) -> dict[str, Any] | None:
        new_uid = candidate_unique_ids.get(entity_entry.entity_id)
        if new_uid is None:
            return None

        if candidate_counts.get(new_uid, 0) > 1:
            _LOGGER.info(
                "Skipping unique_id migration for %s because target would collide: %s",
                entity_entry.entity_id,
                new_uid,
            )
            return None

        conflict_entity_id = registry.async_get_entity_id(
            entity_entry.domain,
            entity_entry.platform,
            new_uid,
        )
        if conflict_entity_id and conflict_entity_id != entity_entry.entity_id:
            _LOGGER.info(
                "Removing duplicate entity %s to keep existing stable unique_id %s",
                entity_entry.entity_id,
                new_uid,
            )
            registry.async_remove(entity_entry.entity_id)
            return None

        return {"new_unique_id": new_uid}

    await er.async_migrate_entries(hass, entry.entry_id, _migrate_unique_id)


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

    subentry_id_map: dict[str, str] = {}
    existing_names = _collect_subentry_names(entry)

    for subentry in list(entry.subentries.values()):
        data = dict(subentry.data)
        if data.get(CONF_ELEMENT_TYPE) != _CONNECTION_TYPE:
            continue

        endpoints = data.get(connection.SECTION_ENDPOINTS, {})
        if not isinstance(endpoints, dict):
            endpoints = {}
        source_name = get_connection_target_name(endpoints.get(connection.CONF_SOURCE)) or ""
        target_name = get_connection_target_name(endpoints.get(connection.CONF_TARGET)) or ""

        forward_data, reverse_data = migrate_connection_config(data, existing_names=existing_names)
        hass.config_entries.async_update_subentry(entry, subentry, data=forward_data)
        existing_names.add(subentry.title)

        if reverse_data is None:
            continue

        existing_reverse = _find_reverse_subentry(
            entry,
            source_name=source_name,
            target_name=target_name,
            exclude_subentry_id=subentry.subentry_id,
        )
        if existing_reverse is not None:
            merged = merge_reverse_into_existing(dict(existing_reverse.data), reverse_data)
            hass.config_entries.async_update_subentry(entry, existing_reverse, data=merged)
            _LOGGER.info(
                "Merged reverse connection settings into existing subentry %s",
                existing_reverse.title,
            )
            continue

        reverse_title = str(reverse_data[CONF_NAME])
        new_subentry = ConfigSubentry(
            data=MappingProxyType(reverse_data),
            subentry_type=_CONNECTION_TYPE,
            title=reverse_title,
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(entry, new_subentry)
        existing_names.add(reverse_title)
        subentry_id_map[subentry.subentry_id] = new_subentry.subentry_id
        _LOGGER.info(
            "Created reverse connection subentry %s from %s",
            reverse_title,
            subentry.title,
        )

    if subentry_id_map:
        await _migrate_connection_entity_unique_ids(hass, entry, subentry_id_map=subentry_id_map)

    hass.config_entries.async_update_entry(entry, minor_version=MINOR_VERSION)
    _LOGGER.info("Migration complete for %s entry %s", DOMAIN, entry.entry_id)
    return True
