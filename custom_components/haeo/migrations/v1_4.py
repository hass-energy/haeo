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
    candidate_ids: list[str],
) -> ConfigSubentry | None:
    for subentry_id in candidate_ids:
        subentry = entry.subentries[subentry_id]
        data = dict(subentry.data)
        if data.get(CONF_ELEMENT_TYPE) != _CONNECTION_TYPE:
            continue
        endpoints = data.get(connection.SECTION_ENDPOINTS, {})
        if endpoints_match_reverse(endpoints, source_name=source_name, target_name=target_name):
            return subentry
    return None


async def _migrate_connection_entity_unique_ids(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    reverse_destinations: dict[str, str],
    blocked_subentry_ids: set[str],
) -> None:
    """Move reverse-field input entities to the connection that now holds those fields.

    Entities of connections whose reverse flow was blocked have no destination and
    are removed. When the destination already has an entity for the field, the old
    entity is removed so the destination keeps its own.
    """
    registry = er.async_get(hass)
    candidate_unique_ids: dict[str, str] = {}
    orphaned_entity_ids: set[str] = set()

    for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        parts = entity_entry.unique_id.split("_", 2)
        if len(parts) != _UNIQUE_ID_PART_COUNT:
            continue

        entry_part, subentry_id, unique_key = parts
        new_leaf = _REVERSE_FIELD_RENAMES.get(unique_key.split(".")[-1])
        if new_leaf is None:
            continue

        if subentry_id in blocked_subentry_ids:
            orphaned_entity_ids.add(entity_entry.entity_id)
            continue

        new_subentry_id = reverse_destinations.get(subentry_id)
        if new_subentry_id is None:
            continue

        new_uid = f"{entry_part}_{new_subentry_id}_{new_leaf}"
        candidate_unique_ids[entity_entry.entity_id] = new_uid

    for entity_id in orphaned_entity_ids:
        _LOGGER.info("Removing %s because its connection blocked reverse flow", entity_id)
        registry.async_remove(entity_id)

    def _migrate_unique_id(entity_entry: er.RegistryEntry) -> dict[str, Any] | None:
        new_uid = candidate_unique_ids.get(entity_entry.entity_id)
        if new_uid is None:
            return None

        conflict_entity_id = registry.async_get_entity_id(
            entity_entry.domain,
            entity_entry.platform,
            new_uid,
        )
        if conflict_entity_id is not None:
            _LOGGER.info(
                "Removing %s because another entity already holds unique_id %s",
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

    original_subentry_ids = list(entry.subentries)
    reverse_destinations: dict[str, str] = {}
    blocked_subentry_ids: set[str] = set()
    existing_names = _collect_subentry_names(entry)

    for subentry_id in original_subentry_ids:
        subentry = entry.subentries[subentry_id]
        data = dict(subentry.data)
        if data.get(CONF_ELEMENT_TYPE) != _CONNECTION_TYPE:
            continue

        endpoints = data[connection.SECTION_ENDPOINTS]
        source_name = get_connection_target_name(endpoints[connection.CONF_SOURCE]) or ""
        target_name = get_connection_target_name(endpoints[connection.CONF_TARGET]) or ""

        forward_data, reverse_data = migrate_connection_config(data, existing_names=existing_names)
        hass.config_entries.async_update_subentry(entry, subentry, data=forward_data)

        if reverse_data is None:
            blocked_subentry_ids.add(subentry_id)
            _LOGGER.info("Connection %s blocked reverse flow; no reverse connection created", subentry.title)
            continue

        existing_reverse = _find_reverse_subentry(
            entry,
            source_name=source_name,
            target_name=target_name,
            candidate_ids=[candidate for candidate in original_subentry_ids if candidate != subentry_id],
        )
        if existing_reverse is not None:
            merged = merge_reverse_into_existing(dict(existing_reverse.data), reverse_data)
            hass.config_entries.async_update_subentry(entry, existing_reverse, data=merged)
            reverse_destinations[subentry_id] = existing_reverse.subentry_id
            _LOGGER.info(
                "Merged reverse connection settings from %s into existing subentry %s",
                subentry.title,
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
        reverse_destinations[subentry_id] = new_subentry.subentry_id
        _LOGGER.info(
            "Created reverse connection subentry %s from %s",
            reverse_title,
            subentry.title,
        )

    await _migrate_connection_entity_unique_ids(
        hass,
        entry,
        reverse_destinations=reverse_destinations,
        blocked_subentry_ids=blocked_subentry_ids,
    )

    hass.config_entries.async_update_entry(entry, minor_version=MINOR_VERSION)
    _LOGGER.info("Migration complete for %s entry %s", DOMAIN, entry.entry_id)
    return True
