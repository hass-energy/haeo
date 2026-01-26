"""The Home Assistant Energy Optimizer integration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.typing import ConfigType

from custom_components.haeo.const import (
    CONF_ADVANCED_MODE,
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON_PRESET,
    CONF_NAME,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_TIER_1_COUNT,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_2_COUNT,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_COUNT,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_COUNT,
    DEFAULT_TIER_4_DURATION,
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
)
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.flows import (
    HORIZON_PRESET_5_DAYS,
    HUB_SECTION_ADVANCED,
    HUB_SECTION_BASIC,
    HUB_SECTION_TIERS,
)
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.services import async_setup_services

if TYPE_CHECKING:
    from custom_components.haeo.elements import InputFieldPath
    from custom_components.haeo.entities.auto_optimize_switch import AutoOptimizeSwitch
    from custom_components.haeo.entities.haeo_number import HaeoInputNumber
    from custom_components.haeo.entities.haeo_switch import HaeoInputSwitch

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER, Platform.SWITCH]

# Platforms that provide input entities (must be set up before coordinator)
INPUT_PLATFORMS: list[Platform] = [Platform.NUMBER, Platform.SWITCH]

# Platforms that consume coordinator data (set up after coordinator)
OUTPUT_PLATFORMS: list[Platform] = [Platform.SENSOR]

MIGRATION_MINOR_VERSION = 2


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up the HAEO integration.

    Registers domain-level services that are available even before any config entries are loaded.
    """
    await async_setup_services(hass)
    return True


def _migrate_hub_data(entry: ConfigEntry) -> tuple[dict[str, Any], dict[str, Any]]:
    """Migrate hub entry data/options into sectioned config data."""
    data = dict(entry.data)
    options = dict(entry.options)

    if HUB_SECTION_BASIC in data and HUB_SECTION_ADVANCED in data and HUB_SECTION_TIERS in data:
        return data, options

    horizon_preset = options.get(CONF_HORIZON_PRESET) or data.get(CONF_HORIZON_PRESET) or HORIZON_PRESET_5_DAYS
    tiers = {
        CONF_TIER_1_COUNT: options.get(CONF_TIER_1_COUNT, DEFAULT_TIER_1_COUNT),
        CONF_TIER_1_DURATION: options.get(CONF_TIER_1_DURATION, DEFAULT_TIER_1_DURATION),
        CONF_TIER_2_COUNT: options.get(CONF_TIER_2_COUNT, DEFAULT_TIER_2_COUNT),
        CONF_TIER_2_DURATION: options.get(CONF_TIER_2_DURATION, DEFAULT_TIER_2_DURATION),
        CONF_TIER_3_COUNT: options.get(CONF_TIER_3_COUNT, DEFAULT_TIER_3_COUNT),
        CONF_TIER_3_DURATION: options.get(CONF_TIER_3_DURATION, DEFAULT_TIER_3_DURATION),
        CONF_TIER_4_COUNT: options.get(CONF_TIER_4_COUNT, DEFAULT_TIER_4_COUNT),
        CONF_TIER_4_DURATION: options.get(CONF_TIER_4_DURATION, DEFAULT_TIER_4_DURATION),
    }
    advanced = {
        CONF_DEBOUNCE_SECONDS: options.get(CONF_DEBOUNCE_SECONDS, DEFAULT_DEBOUNCE_SECONDS),
        CONF_ADVANCED_MODE: options.get(CONF_ADVANCED_MODE, False),
    }

    data[HUB_SECTION_BASIC] = {CONF_NAME: data.get(CONF_NAME, entry.title), CONF_HORIZON_PRESET: horizon_preset}
    data[HUB_SECTION_TIERS] = tiers
    data[HUB_SECTION_ADVANCED] = advanced

    for key in (
        CONF_NAME,
        CONF_HORIZON_PRESET,
        CONF_ADVANCED_MODE,
        CONF_DEBOUNCE_SECONDS,
        CONF_TIER_1_COUNT,
        CONF_TIER_1_DURATION,
        CONF_TIER_2_COUNT,
        CONF_TIER_2_DURATION,
        CONF_TIER_3_COUNT,
        CONF_TIER_3_DURATION,
        CONF_TIER_4_COUNT,
        CONF_TIER_4_DURATION,
    ):
        data.pop(key, None)

    return data, {}


def _migrate_subentry_data(subentry: ConfigSubentry) -> dict[str, Any] | None:
    """Migrate a subentry's data to sectioned config if needed."""
    data = dict(subentry.data)
    element_type = data.get(CONF_ELEMENT_TYPE)
    if not element_type or element_type == ELEMENT_TYPE_NETWORK:
        return None

    # Skip if already sectioned
    if any(key in data for key in ("basic", "limits", "advanced", "inputs", "pricing")):
        return None

    from custom_components.haeo.elements import (  # noqa: PLC0415
        battery,
        battery_section,
        connection,
        grid,
        inverter,
        load,
        node,
        solar,
    )

    def add_if_present(target: dict[str, Any], key: str) -> None:
        if key in data and data[key] is not None:
            target[key] = data[key]

    migrated: dict[str, Any] = {CONF_ELEMENT_TYPE: element_type}

    if element_type == battery.ELEMENT_TYPE:
        basic: dict[str, Any] = {}
        limits: dict[str, Any] = {}
        advanced: dict[str, Any] = {}
        undercharge: dict[str, Any] = {}
        overcharge: dict[str, Any] = {}

        for key in (CONF_NAME, battery.CONF_CONNECTION, battery.CONF_CAPACITY, battery.CONF_INITIAL_CHARGE_PERCENTAGE):
            add_if_present(basic, key)
        for key in (
            battery.CONF_MIN_CHARGE_PERCENTAGE,
            battery.CONF_MAX_CHARGE_PERCENTAGE,
            battery.CONF_MAX_CHARGE_POWER,
            battery.CONF_MAX_DISCHARGE_POWER,
        ):
            add_if_present(limits, key)
        for key in (
            battery.CONF_EFFICIENCY,
            battery.CONF_EARLY_CHARGE_INCENTIVE,
            battery.CONF_DISCHARGE_COST,
            battery.CONF_CONFIGURE_PARTITIONS,
        ):
            add_if_present(advanced, key)
        if isinstance(data.get(battery.CONF_SECTION_UNDERCHARGE), dict):
            undercharge.update(data[battery.CONF_SECTION_UNDERCHARGE])
        if isinstance(data.get(battery.CONF_SECTION_OVERCHARGE), dict):
            overcharge.update(data[battery.CONF_SECTION_OVERCHARGE])

        migrated |= {
            battery.CONF_SECTION_BASIC: basic,
            battery.CONF_SECTION_LIMITS: limits,
            battery.CONF_SECTION_ADVANCED: advanced,
            battery.CONF_SECTION_UNDERCHARGE: undercharge,
            battery.CONF_SECTION_OVERCHARGE: overcharge,
        }
        return migrated

    if element_type == battery_section.ELEMENT_TYPE:
        basic: dict[str, Any] = {}
        inputs: dict[str, Any] = {}
        add_if_present(basic, CONF_NAME)
        add_if_present(inputs, battery_section.CONF_CAPACITY)
        add_if_present(inputs, battery_section.CONF_INITIAL_CHARGE)
        migrated |= {
            battery_section.CONF_SECTION_BASIC: basic,
            battery_section.CONF_SECTION_INPUTS: inputs,
        }
        return migrated

    if element_type == connection.ELEMENT_TYPE:
        basic: dict[str, Any] = {}
        limits: dict[str, Any] = {}
        advanced: dict[str, Any] = {}
        for key in (CONF_NAME, connection.CONF_SOURCE, connection.CONF_TARGET):
            add_if_present(basic, key)
        for key in (connection.CONF_MAX_POWER_SOURCE_TARGET, connection.CONF_MAX_POWER_TARGET_SOURCE):
            add_if_present(limits, key)
        for key in (
            connection.CONF_EFFICIENCY_SOURCE_TARGET,
            connection.CONF_EFFICIENCY_TARGET_SOURCE,
            connection.CONF_PRICE_SOURCE_TARGET,
            connection.CONF_PRICE_TARGET_SOURCE,
        ):
            add_if_present(advanced, key)
        migrated |= {
            connection.CONF_SECTION_BASIC: basic,
            connection.CONF_SECTION_LIMITS: limits,
            connection.CONF_SECTION_ADVANCED: advanced,
        }
        return migrated

    if element_type == grid.ELEMENT_TYPE:
        basic: dict[str, Any] = {}
        pricing: dict[str, Any] = {}
        limits: dict[str, Any] = {}
        for key in (CONF_NAME, grid.CONF_CONNECTION):
            add_if_present(basic, key)
        for key in (grid.CONF_IMPORT_PRICE, grid.CONF_EXPORT_PRICE):
            add_if_present(pricing, key)
        for key in (grid.CONF_IMPORT_LIMIT, grid.CONF_EXPORT_LIMIT):
            add_if_present(limits, key)
        migrated |= {
            grid.CONF_SECTION_BASIC: basic,
            grid.CONF_SECTION_PRICING: pricing,
            grid.CONF_SECTION_LIMITS: limits,
        }
        return migrated

    if element_type == inverter.ELEMENT_TYPE:
        basic: dict[str, Any] = {}
        limits: dict[str, Any] = {}
        advanced: dict[str, Any] = {}
        for key in (CONF_NAME, inverter.CONF_CONNECTION):
            add_if_present(basic, key)
        for key in (inverter.CONF_MAX_POWER_DC_TO_AC, inverter.CONF_MAX_POWER_AC_TO_DC):
            add_if_present(limits, key)
        for key in (inverter.CONF_EFFICIENCY_DC_TO_AC, inverter.CONF_EFFICIENCY_AC_TO_DC):
            add_if_present(advanced, key)
        migrated |= {
            inverter.CONF_SECTION_BASIC: basic,
            inverter.CONF_SECTION_LIMITS: limits,
            inverter.CONF_SECTION_ADVANCED: advanced,
        }
        return migrated

    if element_type == load.ELEMENT_TYPE:
        basic: dict[str, Any] = {}
        inputs: dict[str, Any] = {}
        for key in (CONF_NAME, load.CONF_CONNECTION):
            add_if_present(basic, key)
        add_if_present(inputs, load.CONF_FORECAST)
        migrated |= {
            load.CONF_SECTION_BASIC: basic,
            load.CONF_SECTION_INPUTS: inputs,
        }
        return migrated

    if element_type == node.ELEMENT_TYPE:
        basic: dict[str, Any] = {}
        advanced: dict[str, Any] = {}
        add_if_present(basic, CONF_NAME)
        for key in (node.CONF_IS_SOURCE, node.CONF_IS_SINK):
            add_if_present(advanced, key)
        migrated |= {
            node.CONF_SECTION_BASIC: basic,
            node.CONF_SECTION_ADVANCED: advanced,
        }
        return migrated

    if element_type == solar.ELEMENT_TYPE:
        basic: dict[str, Any] = {}
        advanced: dict[str, Any] = {}
        for key in (CONF_NAME, solar.CONF_CONNECTION, solar.CONF_FORECAST):
            add_if_present(basic, key)
        for key in (solar.CONF_CURTAILMENT, solar.CONF_PRICE_PRODUCTION):
            add_if_present(advanced, key)
        migrated |= {
            solar.CONF_SECTION_BASIC: basic,
            solar.CONF_SECTION_ADVANCED: advanced,
        }
        return migrated

    return None


async def async_migrate_entry(hass: HomeAssistant, entry: HaeoConfigEntry) -> bool:
    """Migrate existing config entries to the latest version."""
    if entry.version != 1 or entry.minor_version >= MIGRATION_MINOR_VERSION:
        return True

    _LOGGER.info(
        "Migrating HAEO entry %s to version 1.%s",
        entry.entry_id,
        MIGRATION_MINOR_VERSION,
    )

    new_data, new_options = _migrate_hub_data(entry)
    hass.config_entries.async_update_entry(
        entry,
        data=new_data,
        options=new_options,
        minor_version=MIGRATION_MINOR_VERSION,
    )

    for subentry in entry.subentries.values():
        migrated = _migrate_subentry_data(subentry)
        if migrated is not None:
            hass.config_entries.async_update_subentry(entry, subentry, data=migrated)

    _LOGGER.info("Migration complete for HAEO entry %s", entry.entry_id)
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
    input_entities: dict[tuple[str, InputFieldPath], HaeoInputNumber | HaeoInputSwitch] = field(default_factory=dict)
    auto_optimize_switch: AutoOptimizeSwitch | None = field(default=None)
    coordinator: HaeoDataUpdateCoordinator | None = field(default=None)
    value_update_in_progress: bool = field(default=False)


type HaeoConfigEntry = ConfigEntry[HaeoRuntimeData | None]


async def _ensure_required_subentries(hass: HomeAssistant, hub_entry: ConfigEntry) -> None:
    """Ensure required subentries exist for the hub.

    Creates a Network subentry (for optimization sensors) if missing.
    In non-advanced mode, also creates a Switchboard node if missing.
    """
    from custom_components.haeo.elements import ELEMENT_TYPE_NODE  # noqa: PLC0415
    from custom_components.haeo.elements.node import (  # noqa: PLC0415
        CONF_IS_SINK,
        CONF_IS_SOURCE,
        CONF_SECTION_ADVANCED,
        CONF_SECTION_BASIC,
    )

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
    advanced_mode = hub_entry.data.get(HUB_SECTION_ADVANCED, {}).get(CONF_ADVANCED_MODE, False)
    if not advanced_mode and not has_node:
        _LOGGER.info("Creating Switchboard node for hub %s (non-advanced mode)", hub_entry.entry_id)
        switchboard_name = translations.get(f"component.{DOMAIN}.common.switchboard_node_name", "Switchboard")

        switchboard_subentry = ConfigSubentry(
            data=MappingProxyType(
                {
                    CONF_ELEMENT_TYPE: ELEMENT_TYPE_NODE,
                    CONF_SECTION_BASIC: {CONF_NAME: switchboard_name},
                    CONF_SECTION_ADVANCED: {
                        CONF_IS_SOURCE: False,
                        CONF_IS_SINK: False,
                    },
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

    # Create horizon manager first - input entities and coordinator depend on it
    # This is a pure Python object, not an entity
    horizon_manager = HorizonManager(hass=hass, config_entry=entry)

    # Create runtime data for this setup
    runtime_data = HaeoRuntimeData(horizon_manager=horizon_manager)
    entry.runtime_data = runtime_data

    # Start horizon manager's scheduled updates - returns stop function
    entry.async_on_unload(horizon_manager.start())

    # Set up input platforms first - they populate runtime_data.input_entities
    await hass.config_entries.async_forward_entry_setups(entry, INPUT_PLATFORMS)
    # Register cleanup - will be called on failure or unload
    # Return the coroutine directly - HA will wrap it in async_create_task
    entry.async_on_unload(
        lambda: hass.config_entries.async_unload_platforms(entry, INPUT_PLATFORMS)  # type: ignore[arg-type]
    )

    # Wait for all input entities to have their data ready
    # Each entity signals via asyncio.Event when its forecast data is loaded
    _LOGGER.debug("Waiting for %d input entities to be ready", len(runtime_data.input_entities))
    try:
        async with asyncio.timeout(30):
            await asyncio.gather(*[entity.wait_ready() for entity in runtime_data.input_entities.values()])
    except TimeoutError:
        not_ready = [key for key, entity in runtime_data.input_entities.items() if not entity.is_ready()]
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="input_entities_not_ready",
            translation_placeholders={"not_ready": str(not_ready)},
        ) from None
    _LOGGER.debug("All input entities ready")

    # Create coordinator after input entities are ready - it reads from them
    coordinator = HaeoDataUpdateCoordinator(hass, entry)
    runtime_data.coordinator = coordinator
    # Register coordinator cleanup
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

    # Get all current subentry IDs (devices are keyed by subentry_id, not element name)
    current_subentry_ids = {subentry.subentry_id for subentry in config_entry.subentries.values()}

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
                for subentry_id in current_subentry_ids:
                    if suffix.startswith(f"{subentry_id}_"):
                        # Device belongs to an existing subentry - keep it
                        return False

    # If device has no HAEO identifiers, it's not managed by us - keep it
    if not has_haeo_identifier:
        return False

    # Device doesn't match any current subentry - allow removal
    _LOGGER.info(
        "Removing stale device %s (was associated with removed element)",
        device_entry.name,
    )
    return True
