"""Migration helpers for config entry version 1.4.

Splits bidirectional connections, turns pure-junction nodes into junctions,
replaces the hub's horizon preset and tiers with a horizon choice, turns
battery undercharge and overcharge partitions into buffers, and links element
entities to their element's subentry.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
import logging
from types import MappingProxyType
from typing import NamedTuple

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.adapters.elements.junction import JUNCTION_DEVICE_JUNCTION, JUNCTION_POWER_BALANCE
from custom_components.haeo.core.adapters.elements.node import NODE_DEVICE_NODE, NODE_POWER_BALANCE
from custom_components.haeo.core.const import CONF_ADVANCED_MODE, CONF_NAME, HORIZON_PRESET_DAYS, HUB_SECTION_ADVANCED
from custom_components.haeo.core.schema.elements import battery, buffer, connection, junction, node
from custom_components.haeo.core.schema.migrations import battery_partitions as partitions
from custom_components.haeo.core.schema.migrations.v1_4 import (
    REVERSE_FIELDS,
    connection_route,
    junction_config,
    migrate_battery_config,
    migrate_connection_config,
    migrate_hub_horizon,
    node_becomes_junction,
    node_is_junction,
)
from custom_components.haeo.repairs import create_horizon_tiers_replaced_issue, create_node_replaced_by_junction_issue
from custom_components.haeo.unique_id import element_output_unique_id, element_unique_id, parse_element_unique_id

_LOGGER = logging.getLogger(__name__)

MINOR_VERSION = 4

# Fields that elements no longer have, by the last part of the key their input
# entities are identified by. Partition fields were keyed by their field name,
# after the partition when both partitions were configured.
_REMOVED_FIELDS: Mapping[str, frozenset[str]] = {
    connection.ELEMENT_TYPE: frozenset(REVERSE_FIELDS),
    battery.ELEMENT_TYPE: frozenset(
        (partitions.CONF_CONFIGURE_PARTITIONS, partitions.CONF_PARTITION_PERCENTAGE, partitions.CONF_PARTITION_COST)
    ),
}


class _ElementEntity(NamedTuple):
    """An entity of an element, with the key its unique ID gives after the element's subentry ID."""

    entry: er.RegistryEntry
    key: str


def _element_entities(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, list[_ElementEntity]]:
    """Return the config entry's element entities, by the subentry ID their unique ID names."""
    entities: defaultdict[str, list[_ElementEntity]] = defaultdict(list)
    for entity_entry in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id):
        element = parse_element_unique_id(entry.entry_id, entity_entry.unique_id)
        if element is not None:
            entities[element.subentry_id].append(_ElementEntity(entity_entry, element.key))
    return entities


def _split_connections(hass: HomeAssistant, entry: ConfigEntry, existing_names: set[str]) -> None:
    """Make each connection unidirectional, creating a reverse connection where reverse flow was intended."""
    connections = [s for s in entry.subentries.values() if s.subentry_type == connection.ELEMENT_TYPE]
    routes = {connection_route(subentry.data) for subentry in connections}
    for subentry in connections:
        forward_data, reverse_data = migrate_connection_config(
            subentry.data, existing_names=existing_names, routes=routes
        )
        hass.config_entries.async_update_subentry(entry, subentry, data=forward_data)
        if reverse_data is not None:
            reverse_title = str(reverse_data[CONF_NAME])
            hass.config_entries.async_add_subentry(
                entry,
                ConfigSubentry(
                    data=MappingProxyType(reverse_data),
                    subentry_type=connection.ELEMENT_TYPE,
                    title=reverse_title,
                    unique_id=None,
                ),
            )
            _LOGGER.info("Created reverse connection %s from %s", reverse_title, subentry.title)


def _remove_removed_field_entities(
    hass: HomeAssistant, entry: ConfigEntry, entities: dict[str, list[_ElementEntity]]
) -> None:
    """Remove the input entities of fields their element no longer has, and drop them from ``entities``.

    A connection's reverse-direction values now live on a separate connection,
    which creates its own entities when the integration sets up.
    """
    registry = er.async_get(hass)
    for subentry in entry.subentries.values():
        removed_fields = _REMOVED_FIELDS.get(subentry.subentry_type, frozenset())
        kept: list[_ElementEntity] = []
        for element_entity in entities.get(subentry.subentry_id, []):
            field = element_entity.key.rsplit(".", 1)[-1]
            if field in removed_fields:
                _LOGGER.info(
                    "Removing %s because %s no longer has a %s field",
                    element_entity.entry.entity_id,
                    subentry.title,
                    field,
                )
                registry.async_remove(element_entity.entry.entity_id)
            else:
                kept.append(element_entity)
        entities[subentry.subentry_id] = kept


def _swap_node_for_junction(
    hass: HomeAssistant, entry: ConfigEntry, subentry: ConfigSubentry, entities: list[_ElementEntity]
) -> None:
    """Replace a node subentry with a junction that keeps its subentry ID, device, and sensor.

    Home Assistant deletes a removed subentry's devices and entities, so the
    device is held by the config entry alone and the sensor is detached while
    the subentry is swapped. The junction reuses the subentry ID, and the device
    and sensor are re-keyed to the junction's identifiers, so their IDs,
    customizations, and history carry over. The role switches have no junction
    equivalent and are removed.
    """
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    entry_id, subentry_id = entry.entry_id, subentry.subentry_id
    node_device_key = element_unique_id(entry_id, subentry_id, NODE_DEVICE_NODE)
    junction_device_key = element_unique_id(entry_id, subentry_id, JUNCTION_DEVICE_JUNCTION)
    rekeyed_unique_ids = {
        element_output_unique_id(entry_id, subentry_id, NODE_DEVICE_NODE, NODE_POWER_BALANCE): (
            element_output_unique_id(entry_id, subentry_id, JUNCTION_DEVICE_JUNCTION, JUNCTION_POWER_BALANCE)
        ),
    }

    device = device_registry.async_get_device(identifiers={(DOMAIN, node_device_key)})
    if device is not None:
        device_registry.async_update_device(device.id, add_config_entry_id=entry.entry_id, add_config_subentry_id=None)

    kept_entity_ids: list[str] = []
    for entity_entry, _ in entities:
        new_unique_id = rekeyed_unique_ids.get(entity_entry.unique_id)
        if new_unique_id is None:
            entity_registry.async_remove(entity_entry.entity_id)
            continue
        entity_registry.async_update_entity(
            entity_entry.entity_id, config_subentry_id=None, new_unique_id=new_unique_id
        )
        kept_entity_ids.append(entity_entry.entity_id)

    # Home Assistant 2026.9+ gives a device a single owner, so the config entry link
    # above only takes effect once the subentry link is removed in a separate call.
    # Entities still linked to the subentry would be removed with it, so this follows them
    if device is not None:
        device_registry.async_update_device(
            device.id, remove_config_entry_id=entry.entry_id, remove_config_subentry_id=subentry.subentry_id
        )

    hass.config_entries.async_remove_subentry(entry, subentry.subentry_id)
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data=MappingProxyType(junction_config(subentry.data)),
            subentry_type=junction.ELEMENT_TYPE,
            title=subentry.title,
            unique_id=None,
            subentry_id=subentry.subentry_id,
        ),
    )

    if device is not None:
        device_registry.async_update_device(
            device.id,
            add_config_entry_id=entry.entry_id,
            add_config_subentry_id=subentry.subentry_id,
            new_identifiers={(DOMAIN, junction_device_key)},
        )
    for entity_id in kept_entity_ids:
        entity_registry.async_update_entity(entity_id, config_subentry_id=subentry.subentry_id)
    # Entities linked to the config entry alone would be removed with this link, so it goes last
    if device is not None:
        device_registry.async_update_device(
            device.id, remove_config_entry_id=entry.entry_id, remove_config_subentry_id=None
        )


def _replace_nodes_with_junctions(
    hass: HomeAssistant, entry: ConfigEntry, entities: dict[str, list[_ElementEntity]]
) -> None:
    """Replace nodes with junctions where they should only pass power through.

    The Switchboard is always a junction. Outside advanced mode a node cannot be
    configured, so every node becomes a junction. In advanced mode, other nodes
    become junctions only when neither their source nor sink switch is on. A
    junction has no switches to turn on, and a node whose switch was on gets a
    repair issue saying it no longer produces or consumes power.
    """
    advanced_mode = entry.data.get(HUB_SECTION_ADVANCED, {}).get(CONF_ADVANCED_MODE, False)
    nodes = [s for s in entry.subentries.values() if s.subentry_type == node.ELEMENT_TYPE]
    for subentry in nodes:
        if node_becomes_junction(subentry.data, advanced_mode=advanced_mode):
            if not node_is_junction(subentry.data):
                _LOGGER.warning(
                    "Node %s had its source or sink switch turned on or driven by an entity; "
                    "it is now a junction that only passes power through",
                    subentry.title,
                )
                create_node_replaced_by_junction_issue(hass, entry.entry_id, subentry.title)
            _swap_node_for_junction(hass, entry, subentry, entities.pop(subentry.subentry_id, []))
            _LOGGER.info("Replaced node %s with a junction", subentry.title)


def _migrate_batteries(hass: HomeAssistant, entry: ConfigEntry, existing_names: set[str]) -> None:
    """Move each battery's partitions into buffers for the battery and add the cost of its charge limits."""
    batteries = [s for s in entry.subentries.values() if s.subentry_type == battery.ELEMENT_TYPE]
    for subentry in batteries:
        migration = migrate_battery_config(subentry.data, existing_names=existing_names)
        hass.config_entries.async_update_subentry(entry, subentry, data=migration.battery)
        for buffer_config in migration.buffers:
            title = str(buffer_config[CONF_NAME])
            hass.config_entries.async_add_subentry(
                entry,
                ConfigSubentry(
                    data=MappingProxyType(buffer_config),
                    subentry_type=buffer.ELEMENT_TYPE,
                    title=title,
                    unique_id=None,
                ),
            )
            _LOGGER.info("Created buffer %s from the partitions of battery %s", title, subentry.title)


def _link_entities_to_subentries(
    hass: HomeAssistant, entry: ConfigEntry, entities: dict[str, list[_ElementEntity]]
) -> None:
    """Link unlinked element entities to their subentry, or remove them if it no longer exists.

    Linked entities are removed along with their element. Entities of elements
    deleted before entities were linked are left behind unavailable, so they
    are removed here. Hub entities are linked to the network subentry when
    setup adds them, and entities with unrecognized unique IDs are left alone.
    """
    registry = er.async_get(hass)
    for subentry_id, element_entities in entities.items():
        unlinked = [entity_entry for entity_entry, _ in element_entities if entity_entry.config_subentry_id is None]
        for entity_entry in unlinked:
            if subentry_id in entry.subentries:
                registry.async_update_entity(entity_entry.entity_id, config_subentry_id=subentry_id)
            else:
                _LOGGER.info("Removing %s because its element no longer exists", entity_entry.entity_id)
                registry.async_remove(entity_entry.entity_id)


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

    existing_names = {subentry.title for subentry in entry.subentries.values()}
    _split_connections(hass, entry, existing_names)
    _migrate_batteries(hass, entry, existing_names)

    entities = _element_entities(hass, entry)
    _remove_removed_field_entities(hass, entry, entities)
    _replace_nodes_with_junctions(hass, entry, entities)
    _link_entities_to_subentries(hass, entry, entities)

    horizon = migrate_hub_horizon(entry.data)
    if horizon.tiers_replaced_by is not None:
        days = HORIZON_PRESET_DAYS[horizon.tiers_replaced_by]
        _LOGGER.warning(
            "Hub %s planned over custom horizon tiers, which are no longer supported; it now plans %s days ahead",
            entry.title,
            days,
        )
        create_horizon_tiers_replaced_issue(hass, entry.entry_id, entry.title, days)
    hass.config_entries.async_update_entry(entry, data=horizon.hub, minor_version=MINOR_VERSION)
    _LOGGER.info("Migration complete for %s entry %s", DOMAIN, entry.entry_id)
    return True
