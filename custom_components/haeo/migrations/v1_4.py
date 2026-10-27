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
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.const import (
    CONF_ADVANCED_MODE,
    CONF_ELEMENT_TYPE,
    HORIZON_PRESET_DAYS,
    HUB_SECTION_ADVANCED,
)
from custom_components.haeo.core.schema.elements import battery, connection, junction
from custom_components.haeo.core.schema.migrations import battery_partitions as partitions
from custom_components.haeo.core.schema.migrations.v1_4 import (
    MINOR_VERSION,
    REVERSE_FIELDS,
    junction_config,
    migrate_hub_horizon,
    migrate_participants,
    node_is_junction,
    predates_v1_4,
)
from custom_components.haeo.repairs import create_horizon_tiers_replaced_issue, create_node_replaced_by_junction_issue
from custom_components.haeo.unique_id import element_output_unique_id, element_unique_id, parse_element_unique_id

_LOGGER = logging.getLogger(__name__)


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
    device is moved to the config entry alone and the sensor is detached while
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

    # Moving a device removes its entities still linked to the subentry it leaves,
    # so each move follows the sensor
    device = device_registry.async_get_device(identifiers={(DOMAIN, node_device_key)})
    if device is not None:
        device_registry.async_update_device(device.id, new_config_subentry_id=None)

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

    for entity_id in kept_entity_ids:
        entity_registry.async_update_entity(entity_id, config_subentry_id=subentry.subentry_id)
    if device is not None:
        device_registry.async_update_device(
            device.id, new_config_subentry_id=subentry.subentry_id, new_identifiers={(DOMAIN, junction_device_key)}
        )


def _element_configs(entry: ConfigEntry) -> dict[str, dict[str, object]]:
    """Return the config of each element subentry, with its element type, by title."""
    return {
        subentry.title: {CONF_ELEMENT_TYPE: subentry.subentry_type, **subentry.data}
        for subentry in entry.subentries.values()
        if subentry.subentry_type in ELEMENT_TYPES
    }


def _migrate_elements(hass: HomeAssistant, entry: ConfigEntry, *, advanced_mode: bool) -> tuple[str, ...]:
    """Apply the v1.4 element migrations to the element subentries.

    Changed configs are saved and created elements are added as subentries.
    Nodes are replaced afterwards, since their device and sensor move with them.

    Returns:
        The titles of the nodes to replace with junctions.

    """
    subentries = {
        subentry.title: subentry for subentry in entry.subentries.values() if subentry.subentry_type in ELEMENT_TYPES
    }
    migration = migrate_participants(_element_configs(entry), advanced_mode=advanced_mode)
    for title, subentry in subentries.items():
        config = migration.participants[title]
        if title not in migration.junctions and config != {CONF_ELEMENT_TYPE: subentry.subentry_type, **subentry.data}:
            hass.config_entries.async_update_subentry(entry, subentry, data=config)
    for title, source in migration.created_from.items():
        config = migration.participants[title]
        element_type = str(config[CONF_ELEMENT_TYPE])
        hass.config_entries.async_add_subentry(
            entry,
            ConfigSubentry(data=MappingProxyType(config), subentry_type=element_type, title=title, unique_id=None),
        )
        _LOGGER.info("Created %s %s from %s", element_type, title, source)
    return migration.junctions


def _replace_nodes_with_junctions(
    hass: HomeAssistant, entry: ConfigEntry, titles: tuple[str, ...], entities: dict[str, list[_ElementEntity]]
) -> None:
    """Replace the nodes with these titles by junctions.

    A junction has no switches to turn on, so a node whose switch was on gets a
    repair issue saying it no longer produces or consumes power.
    """
    subentries = {subentry.title: subentry for subentry in entry.subentries.values()}
    for title in titles:
        subentry = subentries[title]
        if not node_is_junction(subentry.data):
            _LOGGER.warning(
                "Node %s had its source or sink switch turned on or driven by an entity; "
                "it is now a junction that only passes power through",
                title,
            )
            create_node_replaced_by_junction_issue(hass, entry.entry_id, title)
        _swap_node_for_junction(hass, entry, subentry, entities.pop(subentry.subentry_id, []))
        _LOGGER.info("Replaced node %s with a junction", title)


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


def _apply_migrations(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, object]:
    """Apply the v1.4 element, entity and horizon migrations, and return the migrated hub config."""
    advanced_mode = entry.data.get(HUB_SECTION_ADVANCED, {}).get(CONF_ADVANCED_MODE, False)
    junctions = _migrate_elements(hass, entry, advanced_mode=advanced_mode)

    entities = _element_entities(hass, entry)
    _remove_removed_field_entities(hass, entry, entities)
    _replace_nodes_with_junctions(hass, entry, junctions, entities)
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
    return horizon.hub


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

    hub = _apply_migrations(hass, entry)
    hass.config_entries.async_update_entry(entry, data=hub, minor_version=MINOR_VERSION)
    _LOGGER.info("Migration complete for %s entry %s", DOMAIN, entry.entry_id)
    return True


async def async_repair_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply the v1.4 migration again to an entry at 1.4 or later that skipped some of its steps.

    Builds of main before 0.5.0rc1 shipped a v1.4 migration that only split
    bidirectional connections, and saved their entries at 1.4, so those entries
    never had the steps added to v1.4 later. The whole migration runs again,
    as it would on an entry from before 1.4, and the minor version is kept for
    the later migrations to continue from. Connections it already split keep
    their split, but outside advanced mode every node becomes a junction.
    """
    if entry.minor_version < MINOR_VERSION:
        return
    if not predates_v1_4(entry.data, _element_configs(entry).values()):
        return

    _LOGGER.warning(
        "%s entry %s is at version 1.%s but skipped steps of the version 1.%s migration; applying them",
        DOMAIN,
        entry.entry_id,
        entry.minor_version,
        MINOR_VERSION,
    )
    hass.config_entries.async_update_entry(entry, data=_apply_migrations(hass, entry))
