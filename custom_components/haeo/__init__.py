"""The Home Assistant Energy Optimization integration."""

import logging
from types import MappingProxyType

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME

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
        data=MappingProxyType({CONF_NAME: "Network", CONF_ELEMENT_TYPE: "network"}),
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


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Remove a device when its corresponding config entry is removed.

    This handles cleanup of stale devices when elements (batteries, grids, etc.)
    are removed from the HAEO network.

    Args:
        hass: Home Assistant instance
        config_entry: The hub config entry
        device_entry: The device to potentially remove

    Returns:
        True if device can be removed, False if it should be kept

    """
    device_registry = dr.async_get(hass)
    if device_registry.async_get(device_entry.id) is None:
        # Device already removed or does not exist; nothing to clean up
        return False

    # Get all current element names from subentries
    current_element_names = {
        name for subentry in config_entry.subentries.values() if isinstance((name := subentry.data.get(CONF_NAME)), str)
    }

    # Check if this device's identifier matches any current element
    # Device identifiers are (DOMAIN, f"{config_entry.entry_id}_{element_name}")
    has_haeo_identifier = False
    for identifier in device_entry.identifiers:
        if identifier[0] == config_entry.domain:
            has_haeo_identifier = True
            # Extract element name from identifier
            identifier_str = identifier[1]

            # Hub device has identifier (DOMAIN, entry_id) without element suffix - always keep
            if identifier_str == config_entry.entry_id:
                return False

            if identifier_str.startswith(f"{config_entry.entry_id}_"):
                element_name = identifier_str.replace(f"{config_entry.entry_id}_", "", 1)

                # If element still exists, keep the device
                if element_name in current_element_names:
                    return False

    # If device has no HAEO identifiers, it's not managed by us - keep it
    if not has_haeo_identifier:
        return False

    # Device doesn't match any current element - allow removal
    _LOGGER.info(
        "Removing stale device %s (was associated with removed element)",
        device_entry.name,
    )
    return True
