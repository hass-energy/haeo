"""The Home Assistant Energy Optimizer integration."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
import logging
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Protocol

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.typing import ConfigType

from custom_components.haeo.const import DOMAIN, ELEMENT_TYPE_NETWORK
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.core.const import CONF_ADVANCED_MODE, CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.elements import ELEMENT_DEVICE_NAMES_BY_TYPE, InputFieldPath
from custom_components.haeo.flows import HUB_SECTION_ADVANCED
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.services import async_setup_services

from . import migrations as _migrations

if TYPE_CHECKING:
    from custom_components.haeo.entities.auto_optimize_switch import AutoOptimizeSwitch

_LOGGER = logging.getLogger(__name__)

async_migrate_entry = _migrations.async_migrate_entry
MIGRATION_MINOR_VERSION = _migrations.MIGRATION_MINOR_VERSION


class InputEntity(Protocol):
    """Protocol for input entities tracked by the runtime data.

    DRIVEN entities are display-only: the coordinator pushes loaded values
    via update_display(). EDITABLE entities also handle user writes that
    persist to the config entry and trigger re-optimization.
    """

    entity_id: str

    def update_display(self, value: Any, forecast_times: Sequence[float]) -> None:
        """Update display state from coordinator-loaded data."""
        ...


type InputEntityKey = tuple[str, InputFieldPath]
type InputEntityMap = dict[InputEntityKey, InputEntity]


def _create_input_entities() -> InputEntityMap:
    return {}


PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER, Platform.SWITCH]

# Platforms that provide input entities (must be set up before coordinator)
INPUT_PLATFORMS: list[Platform] = [Platform.NUMBER, Platform.SWITCH]

# Platforms that consume coordinator data (set up after coordinator)
OUTPUT_PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up the HAEO integration.

    Registers domain-level services that are available even before any config entries are loaded.
    """
    await async_setup_services(hass)
    return True


@dataclass(slots=True)
class HaeoRuntimeData:
    """Runtime data for HAEO integration.

    Attributes:
        horizon_manager: Manager providing forecast time windows.
        input_entities: Dict of input entities keyed by (element_name, field_path).
        auto_optimize_switch: Switch controlling automatic optimization.
        coordinator: Coordinator for network-level optimization (set after input platforms).
        value_update_in_progress: Flag to skip reload when updating entity values.

    """

    horizon_manager: HorizonManager
    input_entities: InputEntityMap = field(default_factory=_create_input_entities)
    auto_optimize_switch: AutoOptimizeSwitch | None = field(default=None)
    coordinator: HaeoDataUpdateCoordinator | None = field(default=None)
    value_update_in_progress: bool = field(default=False)


type HaeoConfigEntry = ConfigEntry[HaeoRuntimeData | None]


async def _ensure_required_subentries(hass: HomeAssistant, hub_entry: ConfigEntry) -> None:
    """Ensure required subentries exist for the hub.

    Creates a Network subentry (for optimization sensors) if missing.
    In non-advanced mode, also creates a Switchboard node if missing.
    """
    from custom_components.haeo.core.schema.elements import ElementType  # noqa: PLC0415
    from custom_components.haeo.core.schema.elements.node import (  # noqa: PLC0415
        CONF_IS_SINK,
        CONF_IS_SOURCE,
        SECTION_ROLE,
    )

    # Check if Network subentry already exists
    has_network = False
    has_node = False

    for subentry in hub_entry.subentries.values():
        if subentry.subentry_type == ELEMENT_TYPE_NETWORK:
            has_network = True
        elif subentry.subentry_type == ElementType.NODE:
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
    advanced_mode = hub_entry.data.get(HUB_SECTION_ADVANCED, {}).get(CONF_ADVANCED_MODE, False)
    if not advanced_mode and not has_node:
        _LOGGER.info("Creating Switchboard node for hub %s (non-advanced mode)", hub_entry.entry_id)
        switchboard_name = translations.get(f"component.{DOMAIN}.common.switchboard_node_name", "Switchboard")

        switchboard_subentry = ConfigSubentry(
            data=MappingProxyType(
                {
                    CONF_ELEMENT_TYPE: ElementType.NODE,
                    CONF_NAME: switchboard_name,
                    SECTION_ROLE: {
                        CONF_IS_SOURCE: False,
                        CONF_IS_SINK: False,
                    },
                }
            ),
            subentry_type=ElementType.NODE,
            title=switchboard_name,
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(hub_entry, switchboard_subentry)
        _LOGGER.debug("Switchboard node created successfully")


async def async_update_listener(hass: HomeAssistant, entry: HaeoConfigEntry) -> None:
    """Handle options update or subentry changes."""
    # Check if this is a value-only update from an input entity
    runtime_data = entry.runtime_data
    if runtime_data and runtime_data.value_update_in_progress:
        # Clear the flag and skip reload - signal optimization is stale
        runtime_data.value_update_in_progress = False
        coordinator = runtime_data.coordinator
        if coordinator:
            _LOGGER.debug("Value update detected, signaling optimization stale")
            coordinator.signal_optimization_stale()
        return

    await _ensure_required_subentries(hass, entry)
    _LOGGER.info("HAEO configuration changed, reloading integration")
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: HaeoConfigEntry) -> bool:
    """Set up Home Assistant Energy Optimizer from a config entry.

    Uses async_on_unload pattern for cleanup registration. Home Assistant
    automatically calls all registered async_on_unload callbacks when setup
    fails (returns False, raises ConfigEntryNotReady, or raises any exception).

    For platform cleanup (async_unload_platforms), we must call it explicitly
    in exception handlers since platforms use async_forward_entry_setups.
    """
    # Import here to avoid circular imports at module level
    from custom_components.haeo.entities.device import get_or_create_network_device  # noqa: PLC0415

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

    # Create network device using centralized device creation
    get_or_create_network_device(hass, entry, network_subentry)

    # Create horizon manager first - coordinator depends on it
    horizon_manager = HorizonManager(hass=hass, config_entry=entry)

    # Create runtime data for this setup
    runtime_data = HaeoRuntimeData(horizon_manager=horizon_manager)
    entry.runtime_data = runtime_data

    # Start horizon manager's scheduled updates - returns stop function
    entry.async_on_unload(horizon_manager.start())

    # Set up input platforms - entities are created without loading data
    # DRIVEN entities are inert, EDITABLE entities initialize from config
    await hass.config_entries.async_forward_entry_setups(entry, INPUT_PLATFORMS)
    entry.async_on_unload(
        lambda: hass.config_entries.async_unload_platforms(entry, INPUT_PLATFORMS)  # type: ignore[arg-type]
    )

    # Create coordinator - it subscribes to source sensors directly
    coordinator = HaeoDataUpdateCoordinator(hass, entry)
    runtime_data.coordinator = coordinator
    entry.async_on_unload(coordinator.cleanup)

    # Wrap coordinator operations to provide meaningful HA error messages
    # Cleanup is handled via async_on_unload callbacks - no explicit cleanup needed here
    try:
        # Initialize the network and set up subscriptions
        # This must happen before the first refresh
        await coordinator.async_initialize()

        # Trigger initial optimization before output platform setup
        # This populates coordinator.data so sensor platform can create output entities
        # Use async_refresh() instead of async_config_entry_first_refresh() to avoid
        # retrying setup if optimization fails (e.g., missing sensor data)
        await coordinator.async_refresh()
    except (ConfigEntryNotReady, ConfigEntryError):
        # Re-raise HA exceptions as-is to preserve translation keys
        raise
    except (ValueError, TypeError, KeyError) as err:
        # Configuration or programming errors - permanent failure
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="setup_failed_permanent",
            translation_placeholders={"error": str(err)},
        ) from err
    except Exception as err:
        # Transient errors (network, sensor availability) - retry
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="setup_failed_transient",
            translation_placeholders={"error": str(err)},
        ) from err

    # Set up output platforms after coordinator has data
    await hass.config_entries.async_forward_entry_setups(entry, OUTPUT_PLATFORMS)
    # Register cleanup - will be called on failure or unload
    # Return the coroutine directly - HA will wrap it in async_create_task
    entry.async_on_unload(
        lambda: hass.config_entries.async_unload_platforms(entry, OUTPUT_PLATFORMS)  # type: ignore[arg-type]
    )

    # Register update listener LAST - after all setup is complete
    # This prevents reload loops from subentry additions during initial setup
    entry.async_on_unload(entry.add_update_listener(async_update_listener))

    _LOGGER.info("HAEO integration setup complete")
    return True


async def async_unload_entry(_hass: HomeAssistant, entry: HaeoConfigEntry) -> bool:
    """Unload a config entry.

    All cleanup is handled via async_on_unload callbacks registered during setup:
    - Platform unloading (INPUT_PLATFORMS, OUTPUT_PLATFORMS)
    - Horizon manager timer
    - Coordinator resources
    - Update listener
    """
    _LOGGER.info("Unloading HAEO integration")

    # Clear runtime data reference
    entry.runtime_data = None

    # All cleanup is handled by async_on_unload callbacks
    return True


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

    # Get all current subentries (devices are keyed by subentry_id, not element name)
    subentries_by_id = {subentry.subentry_id: subentry for subentry in config_entry.subentries.values()}

    # Check if this device's identifier matches any current subentry
    has_haeo_identifier = False
    for identifier in device_entry.identifiers:
        if identifier[0] == DOMAIN:
            has_haeo_identifier = True
            identifier_str = identifier[1]

            # Hub device has identifier (DOMAIN, entry_id) without subentry suffix - always keep
            if identifier_str == config_entry.entry_id:
                return False

            if identifier_str.startswith(f"{config_entry.entry_id}_"):
                # Extract suffix from identifier
                # Pattern: {entry_id}_{subentry_id}_{device_name}
                suffix = identifier_str.replace(f"{config_entry.entry_id}_", "", 1)

                # Check if any current subentry_id is a prefix of the suffix
                # The suffix is subentry_id_device_name, so we check for subentry_id_
                for subentry_id, subentry in subentries_by_id.items():
                    prefix = f"{subentry_id}_"
                    if not suffix.startswith(prefix):
                        continue

                    device_name = suffix.removeprefix(prefix)
                    allowed_device_names = ELEMENT_DEVICE_NAMES_BY_TYPE.get(subentry.subentry_type)
                    if allowed_device_names is None:
                        # Unknown subentry type - keep device to avoid accidental removal
                        return False
                    if device_name in allowed_device_names:
                        # Device belongs to an existing subentry - keep it
                        return False
                    # Device name no longer created for this subentry
                    break

    # If device has no HAEO identifiers, it's not managed by us - keep it
    if not has_haeo_identifier:
        return False

    # Device doesn't match any current subentry or device name - allow removal
    _LOGGER.info(
        "Removing stale device %s (no longer created by this entry)",
        device_entry.name,
    )
    return True
