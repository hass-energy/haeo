"""Tests for configurable entity management."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.haeo.const import CONFIGURABLE_ENTITY_UNIQUE_ID, DOMAIN
from custom_components.haeo.flows.sentinels import async_setup_sentinel_entities, async_unload_sentinel_entities


@pytest.fixture(autouse=True)
async def configurable_entity() -> None:
    """Override the autouse fixture from conftest - these tests manage the entity directly."""


async def test_setup_sentinel_entities_creates_entity(hass: HomeAssistant) -> None:
    """Entity is created when it doesn't exist."""
    registry = er.async_get(hass)

    # Verify entity doesn't exist yet
    entity_id = registry.async_get_entity_id(DOMAIN, DOMAIN, CONFIGURABLE_ENTITY_UNIQUE_ID)
    assert entity_id is None

    # Create the entity
    await async_setup_sentinel_entities(hass)

    # Verify entity was created in registry
    entity_id = registry.async_get_entity_id(DOMAIN, DOMAIN, CONFIGURABLE_ENTITY_UNIQUE_ID)
    assert entity_id == f"{DOMAIN}.configurable_entity"

    # Verify state was set with attributes
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == ""
    assert state.attributes["friendly_name"] == "Configurable Entity"
    assert state.attributes["icon"] == "mdi:tune"

    # Verify registry entry has correct metadata
    entry = registry.async_get(entity_id)
    assert entry is not None
    assert entry.original_name == "Configurable Entity"
    assert entry.original_icon == "mdi:tune"


async def test_setup_sentinel_entities_idempotent(hass: HomeAssistant) -> None:
    """Calling setup multiple times doesn't create duplicates."""
    registry = er.async_get(hass)

    # Create the entity twice
    await async_setup_sentinel_entities(hass)
    await async_setup_sentinel_entities(hass)

    # Should still only have one entity
    entries = [e for e in registry.entities.values() if e.unique_id == CONFIGURABLE_ENTITY_UNIQUE_ID]
    assert len(entries) == 1


async def test_unload_sentinel_entities_removes_entity(hass: HomeAssistant) -> None:
    """Entity is removed when cleanup is called."""
    registry = er.async_get(hass)

    # Create the entity first
    await async_setup_sentinel_entities(hass)
    entity_id = registry.async_get_entity_id(DOMAIN, DOMAIN, CONFIGURABLE_ENTITY_UNIQUE_ID)
    assert entity_id is not None
    assert hass.states.get(entity_id) is not None

    # Clean up
    async_unload_sentinel_entities(hass)

    # Verify entity was removed from registry
    assert registry.async_get_entity_id(DOMAIN, DOMAIN, CONFIGURABLE_ENTITY_UNIQUE_ID) is None

    # Verify state was removed
    assert hass.states.get(entity_id) is None


async def test_unload_sentinel_entities_noop_when_missing(hass: HomeAssistant) -> None:
    """Cleanup doesn't fail when entity doesn't exist."""
    # Should not raise
    async_unload_sentinel_entities(hass)
