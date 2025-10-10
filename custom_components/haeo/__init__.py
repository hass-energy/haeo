"""The Home Assistant Energy Optimization integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import HaeoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

type HaeoConfigEntry = ConfigEntry[HaeoDataUpdateCoordinator | None]


async def async_setup_entry(hass: HomeAssistant, entry: HaeoConfigEntry) -> bool:
    """Set up Home Assistant Energy Optimization from a config entry."""
    _LOGGER.info("Setting up HAEO integration")

    # Store coordinator in runtime data first (required for platform setup)
    coordinator = HaeoDataUpdateCoordinator(hass, entry)
    entry.runtime_data = coordinator

    # Set up platforms first
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Fetch initial data after platforms are set up
    await coordinator.async_refresh()

    _LOGGER.info("HAEO integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HaeoConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading HAEO integration")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Clean up coordinator
        entry.runtime_data = None

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: HaeoConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
