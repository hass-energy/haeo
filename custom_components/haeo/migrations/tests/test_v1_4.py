"""Tests for config entry migration helpers (v1.4)."""

from __future__ import annotations

from types import MappingProxyType

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import CONF_ADVANCED_MODE, CONF_ELEMENT_TYPE, CONF_NAME, HUB_SECTION_ADVANCED
from custom_components.haeo.core.schema import as_connection_target, as_constant_value
from custom_components.haeo.core.schema.elements import connection, junction, node
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


async def test_async_migrate_entry_creates_no_reverse_when_unset(hass: HomeAssistant) -> None:
    """A legacy connection with no reverse fields keeps carrying power in one direction only."""
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

    assert [s.title for s in entry.subentries.values()] == ["Sub board"]


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


async def test_async_migrate_entry_removes_entities_when_merging_into_existing_reverse(hass: HomeAssistant) -> None:
    """Merging into a hand-made reverse connection removes the old reverse-field entities and keeps its own."""
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
    assert registry.async_get(old_power_entity_id) is None
    assert registry.async_get(old_price_entity_id) is None
    assert registry.async_get(existing_price_entity_id) is not None
    merged = entry.subentries[existing_reverse.subentry_id].data
    assert merged[SECTION_POWER_LIMITS] == {CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(8.0)}
    assert merged[SECTION_PRICING] == {CONF_PRICE_SOURCE_TARGET: as_constant_value(0.05)}


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


async def test_async_migrate_entry_removes_reverse_field_entities(hass: HomeAssistant) -> None:
    """Reverse-field entities are removed; the new reverse connection creates its own on setup."""
    entry = _add_hub(hass)
    forward = _legacy_connection(
        "Line",
        "A",
        "B",
        power_limits={
            CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(10.0),
            CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
        },
    )
    hass.config_entries.async_add_subentry(entry, forward)
    reverse_entity_id = _register_number(hass, entry, forward, CONF_MAX_POWER_TARGET_SOURCE)
    forward_entity_id = _register_number(hass, entry, forward, CONF_MAX_POWER_SOURCE_TARGET)

    assert await v1_4.async_migrate_entry(hass, entry)

    registry = er.async_get(hass)
    assert registry.async_get(reverse_entity_id) is None
    assert registry.async_get(forward_entity_id) is not None
    assert len(entry.subentries) == 2


async def test_async_migrate_entry_skips_when_already_current(hass: HomeAssistant) -> None:
    """v1.4 migration is a no-op when minor version is already current."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=4)
    entry.add_to_hass(hass)

    result = await v1_4.async_migrate_entry(hass, entry)
    assert result is True
    assert entry.minor_version == 4


def _add_hub_in_mode(hass: HomeAssistant, *, advanced_mode: bool) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Hub",
        data={CONF_NAME: "Hub", HUB_SECTION_ADVANCED: {CONF_ADVANCED_MODE: advanced_mode}},
        version=1,
        minor_version=3,
    )
    entry.add_to_hass(hass)
    return entry


def _node(name: str, *, is_source: object = False, is_sink: object = False) -> ConfigSubentry:
    return _create_subentry(
        {
            CONF_ELEMENT_TYPE: node.ELEMENT_TYPE,
            CONF_NAME: name,
            node.SECTION_ROLE: {node.CONF_IS_SOURCE: is_source, node.CONF_IS_SINK: is_sink},
        }
    )


def _register_entity(
    hass: HomeAssistant, entry: MockConfigEntry, subentry: ConfigSubentry, domain: str, key: str
) -> str:
    return (
        er.async_get(hass)
        .async_get_or_create(domain, DOMAIN, f"{entry.entry_id}_{subentry.subentry_id}_{key}", config_entry=entry)
        .entity_id
    )


@pytest.mark.parametrize("advanced_mode", [False, True], ids=["standard", "advanced"])
async def test_async_migrate_entry_replaces_junction_node(hass: HomeAssistant, advanced_mode: bool) -> None:
    """A node that neither sources nor sinks becomes a junction, and its old entities are removed."""
    entry = _add_hub_in_mode(hass, advanced_mode=advanced_mode)
    switchboard = _node("Switchboard")
    hass.config_entries.async_add_subentry(entry, switchboard)
    switch_entity_id = _register_entity(hass, entry, switchboard, "switch", node.CONF_IS_SOURCE)
    sensor_entity_id = _register_entity(hass, entry, switchboard, "sensor", "node_power_balance")

    assert await v1_4.async_migrate_entry(hass, entry)

    (replacement,) = entry.subentries.values()
    assert replacement.subentry_type == junction.ELEMENT_TYPE
    assert replacement.title == "Switchboard"
    assert dict(replacement.data) == {CONF_ELEMENT_TYPE: junction.ELEMENT_TYPE, CONF_NAME: "Switchboard"}
    registry = er.async_get(hass)
    assert registry.async_get(switch_entity_id) is None
    assert registry.async_get(sensor_entity_id) is None
    assert not ir.async_get(hass).issues


@pytest.mark.parametrize(
    ("advanced_mode", "name"),
    [
        pytest.param(False, "Sub board", id="standard_mode_node"),
        pytest.param(False, "Switchboard", id="standard_mode_switchboard"),
        pytest.param(True, "Switchboard", id="advanced_mode_switchboard"),
    ],
)
async def test_async_migrate_entry_replaces_source_node_with_repair_issue(
    hass: HomeAssistant, advanced_mode: bool, name: str
) -> None:
    """The Switchboard, and any node outside advanced mode, becomes a junction even with its source switch on."""
    entry = _add_hub_in_mode(hass, advanced_mode=advanced_mode)
    hass.config_entries.async_add_subentry(entry, _node(name, is_source=as_constant_value(True)))

    assert await v1_4.async_migrate_entry(hass, entry)

    (replacement,) = entry.subentries.values()
    assert replacement.subentry_type == junction.ELEMENT_TYPE
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"node_replaced_by_junction_{entry.entry_id}_{name}")
    assert issue is not None
    assert issue.translation_placeholders == {"element_name": name}


async def test_async_migrate_entry_keeps_source_node_in_advanced_mode(hass: HomeAssistant) -> None:
    """In advanced mode a node other than the Switchboard that sources or sinks power stays a node."""
    entry = _add_hub_in_mode(hass, advanced_mode=True)
    grid_node = _node("Grid point", is_source=True, is_sink=True)
    hass.config_entries.async_add_subentry(entry, grid_node)

    assert await v1_4.async_migrate_entry(hass, entry)

    assert entry.subentries[grid_node.subentry_id] == grid_node
