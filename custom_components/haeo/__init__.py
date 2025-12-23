"""The Home Assistant Energy Optimizer integration."""

import logging
from types import MappingProxyType

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.haeo.const import CONF_ADVANCED_MODE, CONF_ELEMENT_TYPE, CONF_NAME, ELEMENT_TYPE_NETWORK

from .coordinator import HaeoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

type HaeoConfigEntry = ConfigEntry[HaeoDataUpdateCoordinator | None]


async def _ensure_required_subentries(hass: HomeAssistant, hub_entry: ConfigEntry) -> None:
    """Ensure required subentries exist for the hub.

    This ensures:
    1. A Network subentry exists (for optimization sensors)
    2. In non-advanced mode, a Switchboard node exists

    Args:
        hass: Home Assistant instance
        hub_entry: The hub config entry

    """
    from homeassistant.helpers.translation import async_get_translations  # noqa: PLC0415

    from custom_components.haeo.elements import ELEMENT_TYPE_NODE  # noqa: PLC0415
    from custom_components.haeo.elements.node import CONF_IS_SINK, CONF_IS_SOURCE  # noqa: PLC0415

    # Check if Network subentry already exists
    has_network = False
    has_node = False

    for subentry in hub_entry.subentries.values():
        if subentry.subentry_type == ELEMENT_TYPE_NETWORK:
            has_network = True
        elif subentry.subentry_type == ELEMENT_TYPE_NODE:
            has_node = True
        if has_network and has_node:
            break

    # Create Network subentry if missing
    if not has_network:
        _LOGGER.info("Creating Network subentry for hub %s", hub_entry.entry_id)
        network_subentry = ConfigSubentry(
            data=MappingProxyType({CONF_NAME: hub_entry.title, CONF_ELEMENT_TYPE: ELEMENT_TYPE_NETWORK}),
            subentry_type=ELEMENT_TYPE_NETWORK,
            title=hub_entry.title,
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(hub_entry, network_subentry)
        _LOGGER.debug("Network subentry created successfully")

    # In non-advanced mode, ensure switchboard node exists
    advanced_mode = hub_entry.data.get(CONF_ADVANCED_MODE, False)
    if not advanced_mode and not has_node:
        _LOGGER.info("Creating Switchboard node for hub %s (non-advanced mode)", hub_entry.entry_id)

        # Resolve the switchboard node name from translations
        translations = await async_get_translations(hass, hass.config.language, "common", integrations=["haeo"])
        switchboard_name = translations.get("component.haeo.common.switchboard_node_name", "Switchboard")

        switchboard_subentry = ConfigSubentry(
            data=MappingProxyType(
                {
                    CONF_NAME: switchboard_name,
                    CONF_ELEMENT_TYPE: ELEMENT_TYPE_NODE,
                    CONF_IS_SOURCE: False,
                    CONF_IS_SINK: False,
                }
            ),
            subentry_type=ELEMENT_TYPE_NODE,
            title=switchboard_name,
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(hub_entry, switchboard_subentry)
        _LOGGER.debug("Switchboard node created successfully")


async def async_update_listener(hass: HomeAssistant, entry: HaeoConfigEntry) -> None:
    """Handle options update or subentry changes."""
    from .network import evaluate_network_connectivity  # noqa: PLC0415

    await _ensure_required_subentries(hass, entry)
    await evaluate_network_connectivity(hass, entry)
    _LOGGER.info("HAEO configuration changed, reloading integration")
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: HaeoConfigEntry) -> bool:
    """Set up Home Assistant Energy Optimizer from a config entry."""
    _LOGGER.info("Setting up HAEO integration")

    # Ensure required subentries exist (auto-create if missing)
    await _ensure_required_subentries(hass, entry)

    # Store coordinator in runtime data first (required for platform setup)
    coordinator = HaeoDataUpdateCoordinator(hass, entry)
    entry.runtime_data = coordinator

    # Register update listener for config changes and subentry additions/removals
    entry.async_on_unload(entry.add_update_listener(async_update_listener))

    # Trigger initial optimization on startup
    await coordinator.async_config_entry_first_refresh()

    # Set up platforms - Home Assistant will handle waiting for them
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

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
