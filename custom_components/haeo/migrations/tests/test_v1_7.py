"""Tests for the config entry version 1.7 migration."""

from __future__ import annotations

from types import MappingProxyType

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
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
    CONF_MAX_POWER_SOURCE_TARGET,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)
from custom_components.haeo.migrations import v1_7


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
