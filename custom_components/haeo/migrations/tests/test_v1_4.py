"""Tests for config entry migration helpers (v1.4)."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_connection_target, as_constant_value
from custom_components.haeo.core.schema.elements import connection
from custom_components.haeo.core.schema.sections import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)
from custom_components.haeo.migrations import v1_4


def _create_subentry(data: dict[str, Any], *, subentry_type: str | None = None) -> ConfigSubentry:
    return ConfigSubentry(
        data=MappingProxyType(data),
        subentry_type=subentry_type or str(data.get(CONF_ELEMENT_TYPE, "unknown")),
        title=str(data.get(CONF_NAME, "unnamed")),
        unique_id=None,
    )


async def test_async_migrate_entry_splits_reverse_connection(hass: HomeAssistant) -> None:
    """v1.4 migration creates a reverse connection subentry from reverse-direction fields."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=3)
    entry.add_to_hass(hass)

    connection_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: connection.ELEMENT_TYPE,
            CONF_NAME: "DC to AC",
            connection.SECTION_ENDPOINTS: {
                connection.CONF_SOURCE: as_connection_target("DC Bus"),
                connection.CONF_TARGET: as_connection_target("AC Bus"),
            },
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(10.0),
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(8.0),
            },
            SECTION_PRICING: {
                CONF_PRICE_TARGET_SOURCE: as_constant_value(0.2),
            },
            SECTION_EFFICIENCY: {},
            "segment_order": {"mirror_segment_order": True},
        },
        subentry_type=connection.ELEMENT_TYPE,
    )
    hass.config_entries.async_add_subentry(entry, connection_subentry)

    result = await v1_4.async_migrate_entry(hass, entry)
    assert result is True
    assert entry.minor_version == v1_4.MINOR_VERSION

    connections = [s for s in entry.subentries.values() if s.subentry_type == connection.ELEMENT_TYPE]
    assert len(connections) == 2

    forward = next(s for s in connections if s.title == "DC to AC")
    assert CONF_MAX_POWER_TARGET_SOURCE not in forward.data[SECTION_POWER_LIMITS]
    assert "segment_order" not in forward.data
    assert forward.data[SECTION_POWER_LIMITS][CONF_MAX_POWER_SOURCE_TARGET] == as_constant_value(10.0)

    reverse = next(s for s in connections if s.title != "DC to AC")
    assert reverse.title == "DC to AC (AC Bus to DC Bus)"
    assert reverse.data[SECTION_POWER_LIMITS][CONF_MAX_POWER_SOURCE_TARGET] == as_constant_value(8.0)
    assert reverse.data[SECTION_PRICING][CONF_PRICE_SOURCE_TARGET] == as_constant_value(0.2)


async def test_async_migrate_entry_merges_into_existing_reverse(hass: HomeAssistant) -> None:
    """v1.4 migration merges reverse values into an existing reverse connection."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=3)
    entry.add_to_hass(hass)

    forward_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: connection.ELEMENT_TYPE,
            CONF_NAME: "DC to AC",
            connection.SECTION_ENDPOINTS: {
                connection.CONF_SOURCE: as_connection_target("DC Bus"),
                connection.CONF_TARGET: as_connection_target("AC Bus"),
            },
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(8.0),
            },
            SECTION_PRICING: {},
            SECTION_EFFICIENCY: {},
        },
        subentry_type=connection.ELEMENT_TYPE,
    )
    reverse_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: connection.ELEMENT_TYPE,
            CONF_NAME: "DC to AC (AC Bus to DC Bus)",
            connection.SECTION_ENDPOINTS: {
                connection.CONF_SOURCE: as_connection_target("AC Bus"),
                connection.CONF_TARGET: as_connection_target("DC Bus"),
            },
            SECTION_POWER_LIMITS: {},
            SECTION_PRICING: {
                CONF_PRICE_SOURCE_TARGET: as_constant_value(0.05),
            },
            SECTION_EFFICIENCY: {},
        },
        subentry_type=connection.ELEMENT_TYPE,
    )
    hass.config_entries.async_add_subentry(entry, forward_subentry)
    hass.config_entries.async_add_subentry(entry, reverse_subentry)

    result = await v1_4.async_migrate_entry(hass, entry)
    assert result is True

    connections = [s for s in entry.subentries.values() if s.subentry_type == connection.ELEMENT_TYPE]
    assert len(connections) == 2

    reverse = next(s for s in connections if s.title == "DC to AC (AC Bus to DC Bus)")
    assert reverse.data[SECTION_POWER_LIMITS][CONF_MAX_POWER_SOURCE_TARGET] == as_constant_value(8.0)
    assert reverse.data[SECTION_PRICING][CONF_PRICE_SOURCE_TARGET] == as_constant_value(0.05)


async def test_async_migrate_entry_moves_reverse_entity_unique_id(hass: HomeAssistant) -> None:
    """v1.4 migration re-homes input entity unique IDs for reverse-direction fields."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=3)
    entry.add_to_hass(hass)

    connection_subentry = _create_subentry(
        {
            CONF_ELEMENT_TYPE: connection.ELEMENT_TYPE,
            CONF_NAME: "Line",
            connection.SECTION_ENDPOINTS: {
                connection.CONF_SOURCE: as_connection_target("A"),
                connection.CONF_TARGET: as_connection_target("B"),
            },
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
            },
            SECTION_PRICING: {},
            SECTION_EFFICIENCY: {},
        },
        subentry_type=connection.ELEMENT_TYPE,
    )
    hass.config_entries.async_add_subentry(entry, connection_subentry)

    registry = er.async_get(hass)
    old_uid = f"{entry.entry_id}_{connection_subentry.subentry_id}_max_power_target_source"
    registry.async_get_or_create(
        "number",
        DOMAIN,
        old_uid,
        config_entry=entry,
        suggested_object_id="line_max_power_target_source",
    )

    result = await v1_4.async_migrate_entry(hass, entry)
    assert result is True

    reverse = next(
        s
        for s in entry.subentries.values()
        if s.subentry_type == connection.ELEMENT_TYPE and s.title != "Line"
    )
    new_uid = f"{entry.entry_id}_{reverse.subentry_id}_max_power_source_target"
    entry_by_uid = registry.async_get_entity_id("number", DOMAIN, new_uid)
    assert entry_by_uid is not None
    assert registry.async_get_entity_id("number", DOMAIN, old_uid) is None


async def test_async_migrate_entry_skips_when_already_current(hass: HomeAssistant) -> None:
    """v1.4 migration is a no-op when minor version is already current."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=4)
    entry.add_to_hass(hass)

    result = await v1_4.async_migrate_entry(hass, entry)
    assert result is True
    assert entry.minor_version == 4
