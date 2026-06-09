"""Scenario test helpers for materializing the full HAEO output surface."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import RegistryEntryDisabler

from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator


async def enable_all_config_entry_entities(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Enable integration-disabled entities registered to a config entry.

    Scenario snapshots assert the full optimization output surface, including
    sensors that are disabled by default for new installs. User-disabled entities
    are left unchanged.
    """
    entity_registry = er.async_get(hass)
    for entry in er.async_entries_for_config_entry(entity_registry, config_entry.entry_id):
        if entry.disabled_by == RegistryEntryDisabler.INTEGRATION:
            entity_registry.async_update_entity(entry.entity_id, disabled_by=None)
    await hass.async_block_till_done(wait_background_tasks=True)


async def refresh_config_entry_output_entities(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Enable integration-disabled entities and materialize every output sensor.

    Disabled-by-default entities are registered but never added to the sensor
    platform. Scenario snapshots need the full output surface, so re-enable
    registry entries and reload the sensor platform without re-running setup.
    """
    await enable_all_config_entry_entities(hass, config_entry)
    await hass.config_entries.async_unload_platforms(config_entry, [Platform.SENSOR])
    await hass.config_entries.async_forward_entry_setups(config_entry, [Platform.SENSOR])
    runtime_data = config_entry.runtime_data
    if runtime_data is None:
        return
    coordinator: HaeoDataUpdateCoordinator | None = runtime_data.coordinator
    if coordinator is not None:
        coordinator.async_update_listeners()
    await hass.async_block_till_done(wait_background_tasks=True)
