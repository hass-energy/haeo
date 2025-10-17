"""The Home Assistant Energy Optimization integration."""

import logging
from types import MappingProxyType

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import HaeoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

type HaeoConfigEntry = ConfigEntry[HaeoDataUpdateCoordinator | None]


async def _ensure_network_subentry(hass: HomeAssistant, hub_entry: ConfigEntry) -> None:
    """Ensure a Network subentry exists for the hub.

    The Network subentry represents the optimization network and holds
    the optimization sensors (Cost, Status, Duration).

    Args:
        hass: Home Assistant instance
        hub_entry: The hub config entry

    """
    # Check if Network subentry already exists
    for subentry in hub_entry.subentries.values():
        if subentry.subentry_type == "network":
            _LOGGER.debug("Network subentry already exists for hub %s", hub_entry.entry_id)
            return

    # Create Network subentry by adding it to the hub's subentries collection
    _LOGGER.info("Creating Network subentry for hub %s", hub_entry.entry_id)

    # Create a ConfigSubentry object and add it to the hub
    network_subentry = ConfigSubentry(
        data=MappingProxyType({"name_value": "Network"}),
        subentry_type="network",
        title="Network",
        unique_id=None,
    )

    hass.config_entries.async_add_subentry(hub_entry, network_subentry)
    _LOGGER.debug("Network subentry created successfully")


async def async_update_listener(hass: HomeAssistant, entry: HaeoConfigEntry) -> None:
    """Handle options update or subentry changes."""
    _LOGGER.info("HAEO configuration changed, reloading integration")
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: HaeoConfigEntry) -> bool:
    """Set up Home Assistant Energy Optimization from a config entry."""
    _LOGGER.info("Setting up HAEO integration")

    # Ensure Network subentry exists (auto-create if missing)
    await _ensure_network_subentry(hass, entry)

    # Store coordinator in runtime data first (required for platform setup)
    coordinator = HaeoDataUpdateCoordinator(hass, entry)
    entry.runtime_data = coordinator

    # Register update listener for config changes and subentry additions/removals
    entry.async_on_unload(entry.add_update_listener(async_update_listener))

    # Set up platforms - Home Assistant will handle waiting for them
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Trigger initial optimization on startup
    await coordinator.async_config_entry_first_refresh()

    _LOGGER.info("HAEO integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HaeoConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading HAEO integration")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Clean up coordinator resources
        coordinator = entry.runtime_data
        if coordinator is not None:
            coordinator.cleanup()
        entry.runtime_data = None

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: HaeoConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
