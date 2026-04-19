"""Tests for config entry migration to version 1.5 (entity unique_id stabilization)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.migrations import v1_5


async def test_v1_5_strips_section_prefix_from_unique_ids(hass: HomeAssistant) -> None:
    """Section-prefixed unique_ids are shortened to field name only."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=4)
    entry.add_to_hass(hass)

    registry = er.async_get(hass)

    # Register entities with old-style section-prefixed unique_ids
    old_capacity = registry.async_get_or_create(
        "number",
        DOMAIN,
        f"{entry.entry_id}_bat001_storage.capacity",
        config_entry=entry,
    )
    old_price = registry.async_get_or_create(
        "number",
        DOMAIN,
        f"{entry.entry_id}_bat001_pricing.price_source_target",
        config_entry=entry,
    )
    registry.async_get_or_create(
        "switch",
        DOMAIN,
        f"{entry.entry_id}_node001_curtailment",
        config_entry=entry,
    )

    result = await v1_5.async_migrate_entry(hass, entry)
    assert result is True
    assert entry.minor_version == 5

    # Section-prefixed unique_ids should be stripped to field name
    # while preserving each entity_id in the registry.
    capacity_entity_id = registry.async_get_entity_id("number", DOMAIN, f"{entry.entry_id}_bat001_capacity")
    price_entity_id = registry.async_get_entity_id("number", DOMAIN, f"{entry.entry_id}_bat001_price_source_target")
    assert capacity_entity_id == old_capacity.entity_id
    assert price_entity_id == old_price.entity_id
    assert registry.async_get_entity_id("number", DOMAIN, f"{entry.entry_id}_bat001_storage.capacity") is None
    assert (
        registry.async_get_entity_id("number", DOMAIN, f"{entry.entry_id}_bat001_pricing.price_source_target")
        is None
    )

    # Already-simple unique_ids should be unchanged
    assert registry.async_get_entity_id("switch", DOMAIN, f"{entry.entry_id}_node001_curtailment")


async def test_v1_5_preserves_list_item_unique_ids(hass: HomeAssistant) -> None:
    """List item unique_ids (e.g. rules.0.price) are preserved."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=4)
    entry.add_to_hass(hass)

    registry = er.async_get(hass)

    registry.async_get_or_create(
        "number",
        DOMAIN,
        f"{entry.entry_id}_pol001_rules.0.price",
        config_entry=entry,
    )

    result = await v1_5.async_migrate_entry(hass, entry)
    assert result is True

    # List item unique_ids should be unchanged
    assert registry.async_get_entity_id("number", DOMAIN, f"{entry.entry_id}_pol001_rules.0.price")


async def test_v1_5_removes_section_prefixed_duplicates_when_target_unique_id_exists(
    hass: HomeAssistant,
) -> None:
    """Duplicate section-prefixed entities are removed when stable unique_id already exists."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=4)
    entry.add_to_hass(hass)

    registry = er.async_get(hass)

    stable_entry = registry.async_get_or_create(
        "number",
        DOMAIN,
        f"{entry.entry_id}_bat001_capacity",
        config_entry=entry,
    )
    duplicate_entry = registry.async_get_or_create(
        "number",
        DOMAIN,
        f"{entry.entry_id}_bat001_storage.capacity",
        config_entry=entry,
    )

    result = await v1_5.async_migrate_entry(hass, entry)
    assert result is True

    assert registry.async_get(stable_entry.entity_id) is not None
    assert registry.async_get(duplicate_entry.entity_id) is None
    assert registry.async_get_entity_id("number", DOMAIN, f"{entry.entry_id}_bat001_capacity") == stable_entry.entity_id
    assert registry.async_get_entity_id("number", DOMAIN, f"{entry.entry_id}_bat001_storage.capacity") is None


async def test_v1_5_skips_already_migrated(hass: HomeAssistant) -> None:
    """Entry already at v1.5 is not modified."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=5)
    entry.add_to_hass(hass)

    result = await v1_5.async_migrate_entry(hass, entry)
    assert result is True
