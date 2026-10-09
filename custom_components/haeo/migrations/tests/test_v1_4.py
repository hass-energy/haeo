"""Tests for config entry migration helpers (v1.4)."""

from __future__ import annotations

from types import MappingProxyType

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_connection_target, as_constant_value
from custom_components.haeo.core.schema.elements import connection
from custom_components.haeo.core.schema.sections import (
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)
from custom_components.haeo.migrations import v1_4


def _create_subentry(data: dict[str, object], *, subentry_type: str | None = None) -> ConfigSubentry:
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


def _legacy_connection(
    name: str,
    source: str,
    target: str,
    *,
    power_limits: dict[str, object] | None = None,
    pricing: dict[str, object] | None = None,
) -> ConfigSubentry:
    return _create_subentry(
        {
            CONF_ELEMENT_TYPE: connection.ELEMENT_TYPE,
            CONF_NAME: name,
            connection.SECTION_ENDPOINTS: {
                connection.CONF_SOURCE: as_connection_target(source),
                connection.CONF_TARGET: as_connection_target(target),
            },
            SECTION_POWER_LIMITS: power_limits or {},
            SECTION_PRICING: pricing or {},
            SECTION_EFFICIENCY: {},
        },
        subentry_type=connection.ELEMENT_TYPE,
    )


def _add_hub(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=3)
    entry.add_to_hass(hass)
    return entry


def _register_number(hass: HomeAssistant, entry: MockConfigEntry, subentry: ConfigSubentry, field: str) -> str:
    registry = er.async_get(hass)
    return registry.async_get_or_create(
        "number",
        DOMAIN,
        f"{entry.entry_id}_{subentry.subentry_id}_{field}",
        config_entry=entry,
    ).entity_id


async def test_async_migrate_entry_creates_unlimited_reverse_when_unset(hass: HomeAssistant) -> None:
    """A legacy connection with no reverse fields gets an unlimited reverse connection."""
    entry = _add_hub(hass)
    hass.config_entries.async_add_subentry(
        entry,
        _legacy_connection(
            "Sub board",
            "Sub board node",
            "Switchboard",
            power_limits={CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(10.0)},
        ),
    )

    assert await v1_4.async_migrate_entry(hass, entry)

    reverse = next(s for s in entry.subentries.values() if s.title != "Sub board")
    assert reverse.title == "Sub board (Switchboard to Sub board node)"
    assert reverse.data[connection.SECTION_ENDPOINTS] == {
        connection.CONF_SOURCE: as_connection_target("Switchboard"),
        connection.CONF_TARGET: as_connection_target("Sub board node"),
    }
    assert reverse.data[SECTION_POWER_LIMITS] == {}
    assert reverse.data[SECTION_PRICING] == {}


async def test_async_migrate_entry_zero_reverse_power_blocks_reverse(hass: HomeAssistant) -> None:
    """A constant 0 reverse max power creates no reverse connection and removes the reverse entity."""
    entry = _add_hub(hass)
    forward = _legacy_connection(
        "Line",
        "A",
        "B",
        power_limits={CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(0.0)},
    )
    hass.config_entries.async_add_subentry(entry, forward)
    reverse_entity_id = _register_number(hass, entry, forward, CONF_MAX_POWER_TARGET_SOURCE)

    assert await v1_4.async_migrate_entry(hass, entry)

    assert [s.title for s in entry.subentries.values()] == ["Line"]
    assert entry.subentries[forward.subentry_id].data[SECTION_POWER_LIMITS] == {}
    assert er.async_get(hass).async_get(reverse_entity_id) is None


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


async def test_async_migrate_entry_rehomes_entities_into_existing_reverse(hass: HomeAssistant) -> None:
    """Reverse-field entities move to a hand-made reverse connection, which keeps its own entities."""
    entry = _add_hub(hass)
    forward = _legacy_connection(
        "Line",
        "A",
        "B",
        power_limits={CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(8.0)},
        pricing={CONF_PRICE_TARGET_SOURCE: as_constant_value(0.2)},
    )
    existing_reverse = _legacy_connection(
        "Return line",
        "B",
        "A",
        pricing={CONF_PRICE_SOURCE_TARGET: as_constant_value(0.05)},
    )
    hass.config_entries.async_add_subentry(entry, forward)
    hass.config_entries.async_add_subentry(entry, existing_reverse)
    old_power_entity_id = _register_number(hass, entry, forward, CONF_MAX_POWER_TARGET_SOURCE)
    old_price_entity_id = _register_number(hass, entry, forward, CONF_PRICE_TARGET_SOURCE)
    existing_price_entity_id = _register_number(hass, entry, existing_reverse, CONF_PRICE_SOURCE_TARGET)

    assert await v1_4.async_migrate_entry(hass, entry)

    registry = er.async_get(hass)
    reverse_prefix = f"{entry.entry_id}_{existing_reverse.subentry_id}"
    assert registry.async_get_entity_id("number", DOMAIN, f"{reverse_prefix}_max_power_source_target") == (
        old_power_entity_id
    )
    assert registry.async_get_entity_id("number", DOMAIN, f"{reverse_prefix}_price_source_target") == (
        existing_price_entity_id
    )
    assert registry.async_get(old_price_entity_id) is None


async def test_async_migrate_entry_pairs_opposing_legacy_connections(hass: HomeAssistant) -> None:
    """Two legacy connections in opposite directions absorb each other's reverse settings."""
    entry = _add_hub(hass)
    a_to_b = _legacy_connection("A to B", "A", "B", power_limits={CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(3.0)})
    b_to_a = _legacy_connection("B to A", "B", "A")
    hass.config_entries.async_add_subentry(entry, a_to_b)
    hass.config_entries.async_add_subentry(entry, b_to_a)

    assert await v1_4.async_migrate_entry(hass, entry)

    assert len(entry.subentries) == 2
    assert entry.subentries[a_to_b.subentry_id].data[SECTION_POWER_LIMITS] == {}
    assert entry.subentries[b_to_a.subentry_id].data[SECTION_POWER_LIMITS] == {
        CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(3.0),
    }


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
        s for s in entry.subentries.values() if s.subentry_type == connection.ELEMENT_TYPE and s.title != "Line"
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
