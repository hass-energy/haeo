"""Tests for repairing entries a pre-release build saved at version 1.4 without every v1.4 step."""

from __future__ import annotations

from types import MappingProxyType

from homeassistant.config_entries import ConfigEntryState, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_INTEGRATION_TYPE, DOMAIN, ELEMENT_TYPE_NETWORK, INTEGRATION_TYPE_HUB
from custom_components.haeo.core.adapters.elements.junction import JUNCTION_DEVICE_JUNCTION, JUNCTION_POWER_BALANCE
from custom_components.haeo.core.adapters.elements.node import NODE_DEVICE_NODE, NODE_POWER_BALANCE
from custom_components.haeo.core.const import (
    CONF_ADVANCED_MODE,
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON,
    CONF_HORIZON_PRESET,
    CONF_NAME,
    HORIZON_PRESET_7_DAYS,
    HUB_SECTION_ADVANCED,
    HUB_SECTION_COMMON,
    HUB_SECTION_TIERS,
)
from custom_components.haeo.core.schema import as_constant_value
from custom_components.haeo.core.schema.elements import battery, buffer, connection, grid, junction, node
from custom_components.haeo.core.schema.elements.conformance import is_element_config_schema
from custom_components.haeo.core.schema.horizon_value import as_horizon_preset_value
from custom_components.haeo.core.schema.migrations import battery_partitions as partitions
from custom_components.haeo.core.schema.migrations.v1_4 import (
    LEGACY_CHARGE_LIMIT_COST,
    connection_route,
    migrate_connection_config,
)
from custom_components.haeo.migrations import MIGRATION_MINOR_VERSION, v1_4
from custom_components.haeo.unique_id import element_output_unique_id

from .test_upgrade import CUSTOM_TIERS, LEGACY_ELEMENTS, SOURCE_NODE, _legacy_hub

FORWARD_LINK = "Generator link"
REVERSE_LINK = f"Generator link (Switchboard to {SOURCE_NODE})"


def _early_v1_4_elements() -> list[dict[str, object]]:
    """Return the legacy elements as the pre-release v1.4 migration left them, with only connections split."""
    names = {str(data[CONF_NAME]) for data in LEGACY_ELEMENTS}
    routes = {connection_route(data) for data in LEGACY_ELEMENTS if data[CONF_ELEMENT_TYPE] == connection.ELEMENT_TYPE}
    elements: list[dict[str, object]] = []
    for data in LEGACY_ELEMENTS:
        if data[CONF_ELEMENT_TYPE] != connection.ELEMENT_TYPE:
            elements.append(data)
            continue
        forward, reverse = migrate_connection_config(data, existing_names=names, routes=routes)
        elements.append(forward)
        if reverse is not None:
            elements.append(reverse)
    return elements


def _early_v1_4_hub(hass: HomeAssistant, *, advanced_mode: bool) -> MockConfigEntry:
    """Add a hub as a pre-release build saved it at version 1.4."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            HUB_SECTION_COMMON: {CONF_NAME: "Home", CONF_HORIZON_PRESET: HORIZON_PRESET_7_DAYS},
            HUB_SECTION_TIERS: CUSTOM_TIERS,
            HUB_SECTION_ADVANCED: {CONF_DEBOUNCE_SECONDS: 2, CONF_ADVANCED_MODE: advanced_mode},
        },
        version=1,
        minor_version=v1_4.MINOR_VERSION,
    )
    entry.add_to_hass(hass)
    for data in _early_v1_4_elements():
        hass.config_entries.async_add_subentry(
            entry,
            ConfigSubentry(
                data=MappingProxyType(data),
                subentry_type=str(data[CONF_ELEMENT_TYPE]),
                title=str(data[CONF_NAME]),
                unique_id=None,
            ),
        )
    return entry


def _subentry_data(entry: MockConfigEntry) -> dict[str, dict[str, object]]:
    return {subentry_id: dict(subentry.data) for subentry_id, subentry in entry.subentries.items()}


async def test_early_v1_4_hub_is_repaired_and_sets_up(hass: HomeAssistant) -> None:
    """A hub saved at 1.4 by a pre-release build gets the junction, buffer and horizon steps and sets up."""
    entry = _early_v1_4_hub(hass, advanced_mode=True)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.minor_version == MIGRATION_MINOR_VERSION
    assert entry.data[HUB_SECTION_COMMON] == {
        CONF_NAME: "Home",
        CONF_HORIZON: as_horizon_preset_value(HORIZON_PRESET_7_DAYS),
    }
    assert HUB_SECTION_TIERS not in entry.data
    subentries = {subentry.title: subentry for subentry in entry.subentries.values()}
    assert all(
        is_element_config_schema(dict(subentry.data))
        for subentry in subentries.values()
        if subentry.subentry_type != ELEMENT_TYPE_NETWORK
    )
    assert subentries["Switchboard"].subentry_type == junction.ELEMENT_TYPE
    assert subentries[SOURCE_NODE].subentry_type == node.ELEMENT_TYPE
    assert subentries["Battery reserve"].subentry_type == buffer.ELEMENT_TYPE
    assert subentries["Battery headroom"].subentry_type == buffer.ELEMENT_TYPE
    connections = sorted(title for title, s in subentries.items() if s.subentry_type == connection.ELEMENT_TYPE)
    assert connections == [FORWARD_LINK, REVERSE_LINK]


async def test_grid_and_battery_survive_repair(hass: HomeAssistant) -> None:
    """The repair keeps the grid, and moves the battery's partitions into its limits and buffers."""
    entry = _early_v1_4_hub(hass, advanced_mode=False)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    subentries = {subentry.title: subentry for subentry in entry.subentries.values()}
    assert subentries["Grid"].subentry_type == grid.ELEMENT_TYPE
    battery_data = subentries["Battery"].data
    assert partitions.SECTION_PARTITIONING not in battery_data
    assert battery_data[battery.SECTION_LIMITS] == {
        battery.CONF_MIN_CHARGE_PERCENTAGE: as_constant_value(5.0),
        battery.CONF_MAX_CHARGE_PERCENTAGE: as_constant_value(95.0),
    }
    assert battery_data[battery.SECTION_ADVANCED] == {
        battery.CONF_CHARGE_LIMIT_COST: as_constant_value(LEGACY_CHARGE_LIMIT_COST)
    }


async def test_switchboard_power_balance_sensor_keeps_its_entity_id(hass: HomeAssistant) -> None:
    """The Switchboard's power balance sensor is re-keyed to the junction and keeps its entity ID."""
    entry = _early_v1_4_hub(hass, advanced_mode=False)
    switchboard_id = next(s.subentry_id for s in entry.subentries.values() if s.title == "Switchboard")
    registry = er.async_get(hass)
    sensor = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        element_output_unique_id(entry.entry_id, switchboard_id, NODE_DEVICE_NODE, NODE_POWER_BALANCE),
        config_entry=entry,
        suggested_object_id="switchboard_power_balance_shadow_price",
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    migrated = registry.async_get(sensor.entity_id)
    assert migrated is not None
    assert migrated.unique_id == element_output_unique_id(
        entry.entry_id, switchboard_id, JUNCTION_DEVICE_JUNCTION, JUNCTION_POWER_BALANCE
    )
    assert migrated.config_subentry_id == switchboard_id


async def test_current_hub_is_not_repaired(hass: HomeAssistant) -> None:
    """A hub the full migration brought up to date is left unchanged."""
    entry = _legacy_hub(hass, preset=HORIZON_PRESET_7_DAYS, advanced_mode=True)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    data = dict(entry.data)
    subentries = _subentry_data(entry)

    await v1_4.async_repair_entry(hass, entry)

    assert dict(entry.data) == data
    assert _subentry_data(entry) == subentries


async def test_current_source_node_outside_advanced_mode_is_kept(hass: HomeAssistant) -> None:
    """A current hub at 1.4 outside advanced mode keeps a node that sources power."""
    entry = _legacy_hub(hass, preset=HORIZON_PRESET_7_DAYS, advanced_mode=True)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)
    advanced = {**entry.data[HUB_SECTION_ADVANCED], CONF_ADVANCED_MODE: False}
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, HUB_SECTION_ADVANCED: advanced}, minor_version=v1_4.MINOR_VERSION
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    subentries = {subentry.title: subentry for subentry in entry.subentries.values()}
    assert subentries[SOURCE_NODE].subentry_type == node.ELEMENT_TYPE


async def test_entry_below_v1_4_is_left_to_the_migration(hass: HomeAssistant) -> None:
    """The repair leaves an entry below 1.4 for the v1.4 migration to bring up to date."""
    entry = _legacy_hub(hass, preset=HORIZON_PRESET_7_DAYS, advanced_mode=False)
    data = dict(entry.data)
    subentries = _subentry_data(entry)

    await v1_4.async_repair_entry(hass, entry)

    assert dict(entry.data) == data
    assert _subentry_data(entry) == subentries
