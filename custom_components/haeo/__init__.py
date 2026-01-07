"""The Home Assistant Energy Optimizer integration."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from types import MappingProxyType
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.translation import async_get_translations

from custom_components.haeo.const import CONF_ADVANCED_MODE, CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN, ELEMENT_TYPE_NETWORK
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.flows.sentinels import async_setup_sentinel_entities, async_unload_sentinel_entities
from custom_components.haeo.horizon import HorizonManager

if TYPE_CHECKING:
    from custom_components.haeo.entities.haeo_number import HaeoInputNumber
    from custom_components.haeo.entities.haeo_switch import HaeoInputSwitch

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER, Platform.SWITCH]

# Platforms that provide input entities (must be set up before coordinator)
INPUT_PLATFORMS: list[Platform] = [Platform.NUMBER, Platform.SWITCH]

# Platforms that consume coordinator data (set up after coordinator)
OUTPUT_PLATFORMS: list[Platform] = [Platform.SENSOR]


@dataclass(slots=True)
class HaeoRuntimeData:
    """Runtime data for HAEO integration.

    Attributes:
        horizon_manager: Manager providing forecast time windows.
        input_entities: Dict of input entities keyed by (element_name, field_name).
        coordinator: Coordinator for network-level optimization (set after input platforms).
        value_update_in_progress: Flag to skip reload when updating entity values.

    """

    horizon_manager: HorizonManager
    input_entities: dict[tuple[str, str], HaeoInputNumber | HaeoInputSwitch] = field(default_factory=dict)
    coordinator: HaeoDataUpdateCoordinator | None = field(default=None)
    value_update_in_progress: bool = field(default=False)


type HaeoConfigEntry = ConfigEntry[HaeoRuntimeData | None]


async def _ensure_required_subentries(hass: HomeAssistant, hub_entry: ConfigEntry) -> None:
    """Ensure required subentries exist for the hub.

    Creates a Network subentry (for optimization sensors) if missing.
    In non-advanced mode, also creates a Switchboard node if missing.
    """
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

    # Load translations for subentry names
    translations = await async_get_translations(hass, hass.config.language, "common", integrations=[DOMAIN])

    # Create Network subentry if missing
    if not has_network:
        _LOGGER.info("Creating Network subentry for hub %s", hub_entry.entry_id)
        network_subentry_name = translations[f"component.{DOMAIN}.common.network_subentry_name"]
        network_subentry = ConfigSubentry(
            data=MappingProxyType({CONF_NAME: network_subentry_name, CONF_ELEMENT_TYPE: ELEMENT_TYPE_NETWORK}),
            subentry_type=ELEMENT_TYPE_NETWORK,
            title=network_subentry_name,
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(hub_entry, network_subentry)
        _LOGGER.debug("Network subentry created successfully")

    # In non-advanced mode, ensure switchboard node exists
    advanced_mode = hub_entry.data.get(CONF_ADVANCED_MODE, False)
    if not advanced_mode and not has_node:
        _LOGGER.info("Creating Switchboard node for hub %s (non-advanced mode)", hub_entry.entry_id)
        switchboard_name = translations.get(f"component.{DOMAIN}.common.switchboard_node_name", "Switchboard")

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

    # Check if this is a value-only update from an input entity
    runtime_data = entry.runtime_data
    if runtime_data is not None and runtime_data.value_update_in_progress:
        # Clear the flag and skip reload - just refresh coordinator
        runtime_data.value_update_in_progress = False
        _LOGGER.debug("Value update detected, refreshing coordinator without reload")
        if runtime_data.coordinator is not None:
            await runtime_data.coordinator.async_refresh()
        return

    await _ensure_required_subentries(hass, entry)
    await evaluate_network_connectivity(hass, entry)
    _LOGGER.info("HAEO configuration changed, reloading integration")
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: HaeoConfigEntry) -> bool:
    """Set up Home Assistant Energy Optimizer from a config entry."""
    # Ensure required subentries exist (auto-create if missing)
    await _ensure_required_subentries(hass, entry)

    # Find network subentry for network device
    network_subentry = next(
        (s for s in entry.subentries.values() if s.subentry_type == ELEMENT_TYPE_NETWORK),
        None,
    )
    if network_subentry is None:
        _LOGGER.error("No network subentry found - cannot create network device")
        return False

    # Create network device
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        identifiers={(DOMAIN, f"{entry.entry_id}_{network_subentry.subentry_id}")},
        config_entry_id=entry.entry_id,
        config_subentry_id=network_subentry.subentry_id,
        translation_key=ELEMENT_TYPE_NETWORK,
        translation_placeholders={"name": network_subentry.title},
    )

    # Create horizon manager first - input entities and coordinator depend on it
    # This is a pure Python object, not an entity
    horizon_manager = HorizonManager(hass=hass, config_entry=entry)

    # Create runtime data for this setup
    runtime_data = HaeoRuntimeData(horizon_manager=horizon_manager)
    entry.runtime_data = runtime_data

    # Set up sentinel entities for config flows
    await async_setup_sentinel_entities(hass)

    # Start horizon manager's scheduled updates
    horizon_manager.start()

    # Register cleanup on unload
    entry.async_on_unload(horizon_manager.stop)

    # Set up input platforms first - they populate runtime_data.input_entities
    # Input entities register themselves synchronously and load their data asynchronously
    # The platform setup functions wait for all data to load before returning
    await hass.config_entries.async_forward_entry_setups(entry, INPUT_PLATFORMS)

    # Create coordinator after input entities are fully loaded - it reads from them
    # All input entity data is now guaranteed to be loaded
    coordinator = HaeoDataUpdateCoordinator(hass, entry)
    runtime_data.coordinator = coordinator

    # Initialize the network and set up subscriptions
    # This must happen before the first refresh
    await coordinator.async_initialize()

    # Trigger initial optimization before output platform setup
    # This populates coordinator.data so sensor platform can create output entities
    # Use async_refresh() instead of async_config_entry_first_refresh() to avoid
    # retrying setup if optimization fails (e.g., missing sensor data)
    await coordinator.async_refresh()

    # Set up output platforms after coordinator has data
    await hass.config_entries.async_forward_entry_setups(entry, OUTPUT_PLATFORMS)

    # Register update listener LAST - after all setup is complete
    # This prevents reload loops from subentry additions during initial setup
    entry.async_on_unload(entry.add_update_listener(async_update_listener))

    _LOGGER.info("HAEO integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HaeoConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading HAEO integration")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Clean up coordinator resources
        runtime_data = entry.runtime_data
        if runtime_data is not None and runtime_data.coordinator is not None:
            runtime_data.coordinator.cleanup()
        entry.runtime_data = None

        # Clean up sentinel entities if this is the last HAEO config entry
        remaining_entries = [e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != entry.entry_id]
        if not remaining_entries:
            async_unload_sentinel_entities(hass)

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
    """Handle cleanup of stale devices when elements are removed from the HAEO network.

    Returns True if device can be removed, False if it should be kept.
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
