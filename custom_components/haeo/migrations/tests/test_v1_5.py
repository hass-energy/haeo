"""Tests for the config entry version 1.5 migration."""

from __future__ import annotations

from types import MappingProxyType

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN, ELEMENT_TYPE_NETWORK
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.migrations import v1_5
from custom_components.haeo.unique_id import element_unique_id, hub_unique_id


async def test_number_entities_of_inputs_now_switches_are_removed(hass: HomeAssistant) -> None:
    """An EV's plugged-in and away numbers are removed, so they do not linger beside the switches replacing them."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=4)
    entry.add_to_hass(hass)
    ev = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: ElementType.EV, CONF_NAME: "Atto 2"}),
        subentry_type=ElementType.EV,
        title="Atto 2",
        unique_id=None,
    )
    network = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: ELEMENT_TYPE_NETWORK, CONF_NAME: "System"}),
        subentry_type=ELEMENT_TYPE_NETWORK,
        title="System",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, ev)
    hass.config_entries.async_add_subentry(entry, network)
    registry = er.async_get(hass)

    def register(domain: str, unique_id: str) -> str:
        return registry.async_get_or_create(domain, DOMAIN, unique_id, config_entry=entry).entity_id

    plugged_in = register("number", element_unique_id(entry.entry_id, ev.subentry_id, "connected"))
    plugged_in_switch = register("switch", element_unique_id(entry.entry_id, ev.subentry_id, "connected"))
    away = register("number", element_unique_id(entry.entry_id, ev.subentry_id, "away"))
    capacity = register("number", element_unique_id(entry.entry_id, ev.subentry_id, "capacity"))
    hub_number = register("number", hub_unique_id(entry.entry_id, "debounce"))

    assert await v1_5.async_migrate_entry(hass, entry)

    assert registry.async_get(plugged_in) is None
    assert registry.async_get(plugged_in_switch) is not None
    assert registry.async_get(away) is None
    assert registry.async_get(capacity) is not None
    assert registry.async_get(hub_number) is not None
    assert entry.minor_version == v1_5.MINOR_VERSION
