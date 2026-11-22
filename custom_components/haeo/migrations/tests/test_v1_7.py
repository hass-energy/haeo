"""Tests for the config entry version 1.7 migration."""

from __future__ import annotations

from types import MappingProxyType

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_connection_target, as_constant_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.connection import (
    CONF_MAX_POWER,
    CONF_SEGMENT_TYPE,
    CONF_SEGMENTS,
    SECTION_ENDPOINTS,
)
from custom_components.haeo.core.schema.sections import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_PRICE_SOURCE_TARGET,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)
from custom_components.haeo.migrations import v1_7
from custom_components.haeo.unique_id import element_unique_id


def _subentry(element_type: ElementType, data: dict[str, object]) -> ConfigSubentry:
    return ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: element_type, **data}),
        subentry_type=element_type,
        title=str(data[CONF_NAME]),
        unique_id=None,
    )


async def test_connections_get_segments_and_other_elements_are_kept(hass: HomeAssistant) -> None:
    """Each connection's sections become segments, other elements stay as they were, and the entry reaches v1.7."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=6)
    entry.add_to_hass(hass)
    endpoints = {"source": as_connection_target("Inverter"), "target": as_connection_target("Switchboard")}
    link = _subentry(
        ElementType.CONNECTION,
        {
            CONF_NAME: "Link",
            SECTION_ENDPOINTS: endpoints,
            SECTION_POWER_LIMITS: {CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(10.0)},
            SECTION_PRICING: {},
            SECTION_EFFICIENCY: {},
        },
    )
    node = _subentry(ElementType.NODE, {CONF_NAME: "Bus"})
    hass.config_entries.async_add_subentry(entry, link)
    hass.config_entries.async_add_subentry(entry, node)

    assert await v1_7.async_migrate_entry(hass, entry)

    assert dict(entry.subentries[link.subentry_id].data) == {
        CONF_ELEMENT_TYPE: ElementType.CONNECTION,
        CONF_NAME: "Link",
        SECTION_ENDPOINTS: endpoints,
        CONF_SEGMENTS: [{CONF_SEGMENT_TYPE: "power_limit", CONF_MAX_POWER: as_constant_value(10.0)}],
    }
    assert entry.subentries[node.subentry_id].data == node.data
    assert entry.minor_version == v1_7.MINOR_VERSION


async def test_connection_input_entities_become_their_segments_entities(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """A set field's entity keeps its entity ID as its segment's entity, and an unset field's entity is removed."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=6)
    entry.add_to_hass(hass)
    link = _subentry(
        ElementType.CONNECTION,
        {
            CONF_NAME: "Link",
            SECTION_ENDPOINTS: {"source": as_connection_target("A"), "target": as_connection_target("B")},
            SECTION_POWER_LIMITS: {},
            SECTION_PRICING: {CONF_PRICE_SOURCE_TARGET: as_constant_value(0.1)},
            SECTION_EFFICIENCY: {CONF_EFFICIENCY_SOURCE_TARGET: as_constant_value(95.0)},
        },
    )
    hass.config_entries.async_add_subentry(entry, link)

    def _entity(key: str) -> str:
        return entity_registry.async_get_or_create(
            "number", DOMAIN, element_unique_id(entry.entry_id, link.subentry_id, key), config_entry=entry
        ).entity_id

    price = _entity(CONF_PRICE_SOURCE_TARGET)
    efficiency = _entity(f"{SECTION_EFFICIENCY}.{CONF_EFFICIENCY_SOURCE_TARGET}")
    limit = _entity(CONF_MAX_POWER_SOURCE_TARGET)

    assert await v1_7.async_migrate_entry(hass, entry)

    def _key(entity_id: str) -> str | None:
        entity = entity_registry.async_get(entity_id)
        return None if entity is None else entity.unique_id.removeprefix(f"{entry.entry_id}_{link.subentry_id}_")

    assert (_key(price), _key(efficiency), _key(limit)) == ("segments.0.price", "segments.1.efficiency", None)
