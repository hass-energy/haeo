"""Migration helpers for config entry version 1.4.

Splits bidirectional connections and turns pure-junction nodes into junctions.
"""

from __future__ import annotations

from collections.abc import Mapping
import logging
from types import MappingProxyType

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.translation import async_get_translations

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import CONF_ADVANCED_MODE, CONF_ELEMENT_TYPE, CONF_NAME, HUB_SECTION_ADVANCED
from custom_components.haeo.core.schema.elements import connection, junction, node
from custom_components.haeo.core.schema.migrations.v1_4 import (
    REVERSE_TO_FORWARD,
    endpoint_name,
    endpoints_match_reverse,
    junction_config,
    merge_reverse_into_existing,
    migrate_connection_config,
    node_is_junction,
)
from custom_components.haeo.repairs import create_node_replaced_by_junction_issue

_LOGGER = logging.getLogger(__name__)

MINOR_VERSION = 4
_CONNECTION_TYPE = connection.ELEMENT_TYPE
_UNIQUE_ID_PART_COUNT = 3

_REVERSE_FIELDS: frozenset[str] = frozenset(reverse_key for reverse_key, _ in REVERSE_TO_FORWARD)


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
        endpoints = data.get(connection.SECTION_ENDPOINTS)
        if isinstance(endpoints, Mapping) and endpoints_match_reverse(
            endpoints, source_name=source_name, target_name=target_name
        ):
            return subentry
    return None


def _remove_reverse_field_entities(hass: HomeAssistant, entry: ConfigEntry, connection_ids: set[str]) -> None:
    """Remove the input entities of connection fields that no longer exist.

    Reverse-direction values now live on a separate connection, which creates its
    own entities with names that match it when the integration sets up.
    """
    registry = er.async_get(hass)
    for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        parts = entity_entry.unique_id.split("_", 2)
        if len(parts) != _UNIQUE_ID_PART_COUNT:
            continue
        _, subentry_id, unique_key = parts
        if subentry_id in connection_ids and unique_key.split(".")[-1] in _REVERSE_FIELDS:
            _LOGGER.info(
                "Removing %s because connections no longer have reverse-direction fields", entity_entry.entity_id
            )
            registry.async_remove(entity_entry.entity_id)


async def _replace_nodes_with_junctions(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Replace nodes with junctions where they should only pass power through.

    The Switchboard is always a junction. Outside advanced mode a node cannot be
    configured, so every node becomes a junction. In advanced mode, other nodes
    become junctions only when neither their source nor sink switch is on. A
    junction has no switches to turn on, and a node whose switch was on gets a
    repair issue saying it no longer produces or consumes power.
    """
    translations = await async_get_translations(hass, hass.config.language, "common", integrations=[DOMAIN])
    switchboard_name = translations.get(f"component.{DOMAIN}.common.switchboard_node_name", "Switchboard")
    advanced_mode = entry.data.get(HUB_SECTION_ADVANCED, {}).get(CONF_ADVANCED_MODE, False)
    registry = er.async_get(hass)
    for subentry in list(entry.subentries.values()):
        if subentry.subentry_type != node.ELEMENT_TYPE:
            continue
        if not node_is_junction(subentry.data):
            if advanced_mode and subentry.title != switchboard_name:
                continue
            _LOGGER.warning(
                "Node %s had its source or sink switch turned on or driven by an entity; "
                "it is now a junction that only passes power through",
                subentry.title,
            )
            create_node_replaced_by_junction_issue(hass, entry.entry_id, subentry.title)

        prefix = f"{entry.entry_id}_{subentry.subentry_id}_"
        for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
            if entity_entry.unique_id.startswith(prefix):
                registry.async_remove(entity_entry.entity_id)
        hass.config_entries.async_remove_subentry(entry, subentry.subentry_id)
        hass.config_entries.async_add_subentry(
            entry,
            ConfigSubentry(
                data=MappingProxyType(junction_config(subentry.data)),
                subentry_type=junction.ELEMENT_TYPE,
                title=subentry.title,
                unique_id=None,
            ),
        )
        _LOGGER.info("Replaced node %s with a junction", subentry.title)


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
    connection_ids: set[str] = set()
    existing_names = _collect_subentry_names(entry)

    for subentry_id in original_subentry_ids:
        subentry = entry.subentries[subentry_id]
        data = dict(subentry.data)
        if data.get(CONF_ELEMENT_TYPE) != _CONNECTION_TYPE:
            continue

        connection_ids.add(subentry_id)
        endpoints = data[connection.SECTION_ENDPOINTS]
        if not isinstance(endpoints, Mapping):
            msg = f"Connection {subentry.title} has no endpoints section"
            raise TypeError(msg)
        source_name = endpoint_name(endpoints[connection.CONF_SOURCE]) or ""
        target_name = endpoint_name(endpoints[connection.CONF_TARGET]) or ""

        forward_data, reverse_data = migrate_connection_config(data, existing_names=existing_names)
        hass.config_entries.async_update_subentry(entry, subentry, data=forward_data)

        if reverse_data is None:
            _LOGGER.info("Connection %s has no reverse settings; no reverse connection created", subentry.title)
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
        _LOGGER.info(
            "Created reverse connection subentry %s from %s",
            reverse_title,
            subentry.title,
        )

    _remove_reverse_field_entities(hass, entry, connection_ids)
    await _replace_nodes_with_junctions(hass, entry)

    hass.config_entries.async_update_entry(entry, minor_version=MINOR_VERSION)
    _LOGGER.info("Migration complete for %s entry %s", DOMAIN, entry.entry_id)
    return True
