"""Tests for config entry migration helpers (v1.5)."""

from __future__ import annotations

from types import MappingProxyType

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN, ELEMENT_TYPE_NETWORK
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.elements import grid, junction
from custom_components.haeo.migrations import v1_5


def _add_subentry(hass: HomeAssistant, entry: MockConfigEntry, element_type: str, name: str) -> ConfigSubentry:
    subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: element_type, CONF_NAME: name}),
        subentry_type=element_type,
        title=name,
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, subentry)
    return subentry


async def test_async_migrate_entry_links_entities_and_removes_orphans(hass: HomeAssistant) -> None:
    """Unlinked element entities are linked to their subentry, and those of deleted elements are removed."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=4)
    entry.add_to_hass(hass)
    _add_subentry(hass, entry, ELEMENT_TYPE_NETWORK, "System")
    grid_subentry = _add_subentry(hass, entry, grid.ELEMENT_TYPE, "Grid")
    switchboard = _add_subentry(hass, entry, junction.ELEMENT_TYPE, "Switchboard")
    deleted_subentry_id = "01KDELETEDELEMENT000000000"
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    grid_device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        config_subentry_id=grid_subentry.subentry_id,
        identifiers={(DOMAIN, f"{entry.entry_id}_{grid_subentry.subentry_id}_grid")},
    )

    def register(domain: str, key: str, *, config_subentry_id: str | None = None) -> str:
        return entity_registry.async_get_or_create(
            domain,
            DOMAIN,
            f"{entry.entry_id}_{key}",
            config_entry=entry,
            config_subentry_id=config_subentry_id,
        ).entity_id

    grid_price = register("number", f"{grid_subentry.subentry_id}_price_source_target")
    entity_registry.async_update_entity(grid_price, device_id=grid_device.id)
    grid_power = register("sensor", f"{grid_subentry.subentry_id}_grid_grid_power_import")
    switchboard_balance = register(
        "sensor",
        f"{switchboard.subentry_id}_junction_junction_power_balance",
        config_subentry_id=switchboard.subentry_id,
    )
    orphan_number = register("number", f"{deleted_subentry_id}_max_power_source_target")
    orphan_sensor = register("sensor", f"{deleted_subentry_id}_connection_connection_power")
    auto_optimize = register("switch", "auto_optimize")
    horizon = register("sensor", "horizon")

    assert await v1_5.async_migrate_entry(hass, entry)

    def linked_subentry(entity_id: str) -> str | None:
        entity_entry = entity_registry.async_get(entity_id)
        assert entity_entry is not None
        return entity_entry.config_subentry_id

    assert linked_subentry(grid_price) == grid_subentry.subentry_id
    assert linked_subentry(grid_power) == grid_subentry.subentry_id
    assert linked_subentry(switchboard_balance) == switchboard.subentry_id
    assert entity_registry.async_get(orphan_number) is None
    assert entity_registry.async_get(orphan_sensor) is None
    # Hub entities are linked to the network when setup adds them
    assert linked_subentry(auto_optimize) is None
    assert linked_subentry(horizon) is None
    assert entry.minor_version == v1_5.MINOR_VERSION

    # Linked entities are now removed along with their element
    hass.config_entries.async_remove_subentry(entry, grid_subentry.subentry_id)
    await hass.async_block_till_done()
    assert entity_registry.async_get(grid_price) is None
    assert entity_registry.async_get(grid_power) is None


async def test_async_migrate_entry_skips_when_already_current(hass: HomeAssistant) -> None:
    """An entry already at version 1.5 is left alone."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=5)
    entry.add_to_hass(hass)
    orphan = er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{entry.entry_id}_01KDELETEDELEMENT000000000_power", config_entry=entry
    )

    assert await v1_5.async_migrate_entry(hass, entry)

    assert er.async_get(hass).async_get(orphan.entity_id) is not None
