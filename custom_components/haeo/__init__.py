"""The Home Assistant Energy Optimizer integration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import hashlib
import logging
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

from homeassistant.components.frontend import DOMAIN as FRONTEND_DOMAIN
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry, ConfigSubentry, ConfigSubentryData
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType
from homeassistant.setup import async_when_setup

from custom_components.haeo.const import (
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
    STATIC_CARD_BUNDLES,
    STATIC_CARD_STATIC_DIR,
    STATIC_CARD_STATIC_PATH,
)
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES, is_element_type
from custom_components.haeo.core.const import CONF_ADVANCED_MODE
from custom_components.haeo.core.schema.elements import ELEMENT_REFERENCE_PRUNERS
from custom_components.haeo.elements import ELEMENT_DEVICE_NAMES_BY_TYPE
from custom_components.haeo.flows import HUB_SECTION_ADVANCED
from custom_components.haeo.flows.hub import async_network_subentry, async_switchboard_subentry
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.input_stores import (
    InputStoreMap,
    build_input_stores,
    raise_for_rejected_input,
    unavailable_input_placeholders,
    unavailable_input_sources,
)
from custom_components.haeo.inputs.calendar_loader import CalendarInputLoader
from custom_components.haeo.inputs.source_loader import SourceInputLoader
from custom_components.haeo.repairs import async_dismiss_entry_issues, sync_unavailable_input_issues
from custom_components.haeo.services import async_setup_services
from custom_components.haeo.unique_id import parse_element_unique_id
from custom_components.haeo.util import network_subentry

from . import migrations as _migrations

if TYPE_CHECKING:
    from custom_components.haeo.entities.auto_optimize_switch import AutoOptimizeSwitch

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

async_migrate_entry = _migrations.async_migrate_entry
MIGRATION_MINOR_VERSION = _migrations.MIGRATION_MINOR_VERSION


def _create_input_stores() -> InputStoreMap:
    return {}


PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER, Platform.SWITCH]

# Platforms that provide input entities (must be set up before coordinator)
INPUT_PLATFORMS: list[Platform] = [Platform.NUMBER, Platform.SWITCH]

# Platforms that consume coordinator data (set up after coordinator)
OUTPUT_PLATFORMS: list[Platform] = [Platform.SENSOR]

# Timeout in seconds for waiting for input entities to be ready
INPUT_ENTITY_READY_TIMEOUT = 5

# Directory holding the built Lovelace card bundles
CARD_STATIC_DIR = Path(__file__).parent / STATIC_CARD_STATIC_DIR


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up the HAEO integration.

    Registers domain-level services that are available even before any config entries are loaded.
    """
    await _async_register_static_frontend_resources(hass)
    await async_setup_services(hass)
    return True


def card_static_url(static_dir: Path) -> str:
    """Return the URL the card bundles in the static directory are served under.

    The URL ends in a hash of every bundle file, so each build is served from a
    URL of its own and browsers can cache it indefinitely.
    """
    digest = hashlib.sha256()
    for path in sorted(static_dir.glob("*.js")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return f"{STATIC_CARD_STATIC_PATH}/{digest.hexdigest()[:12]}"


async def _async_register_static_frontend_resources(hass: HomeAssistant) -> None:
    """Register static frontend resources used by custom Lovelace cards.

    Each card bundle is registered as its own independent Lovelace resource so
    a stale or missing copy of one card cannot break registration of another.
    """
    # Some test/headless contexts do not initialize the HTTP component.
    # Use getattr instead of direct access so static registration can be skipped safely.
    http = getattr(hass, "http", None)
    if http is None:
        _LOGGER.debug("HTTP component unavailable; skipping static card registration")
        return

    available_bundles = [name for name in STATIC_CARD_BUNDLES if (CARD_STATIC_DIR / name).exists()]
    if not available_bundles:
        _LOGGER.debug("No static card bundles found in %s", CARD_STATIC_DIR)
        return

    static_url = await hass.async_add_executor_job(card_static_url, CARD_STATIC_DIR)
    await http.async_register_static_paths([StaticPathConfig(static_url, str(CARD_STATIC_DIR), cache_headers=True)])

    async def _register_card_urls(hass: HomeAssistant, _component: str) -> None:
        """Register each available card bundle as a Lovelace resource."""
        for name in available_bundles:
            add_extra_js_url(hass, f"{static_url}/{name}")

    # add_extra_js_url writes to a registry the frontend component only creates during its
    # own setup, so calling it here would race with startup ordering. Defer registration
    # until frontend is up; the callback runs immediately when it already is.
    async_when_setup(hass, FRONTEND_DOMAIN, _register_card_urls)


@dataclass(slots=True)
class HaeoRuntimeData:
    """Runtime data for HAEO integration.

    Attributes:
        horizon_manager: Manager providing forecast time windows.
        input_stores: Dict of input stores keyed by (element_name, field_path).
        auto_optimize_switch: Switch controlling automatic optimization.
        coordinator: Coordinator for network-level optimization (set after input platforms).
        value_update_in_progress: Flag to skip reload when updating entity values.
        reload_pending: Flag to coalesce deferred reloads during an element config flow.

    """

    horizon_manager: HorizonManager
    input_stores: InputStoreMap = field(default_factory=_create_input_stores)
    auto_optimize_switch: AutoOptimizeSwitch | None = field(default=None)
    coordinator: HaeoDataUpdateCoordinator | None = field(default=None)
    value_update_in_progress: bool = field(default=False)
    reload_pending: bool = field(default=False)


type HaeoConfigEntry = ConfigEntry[HaeoRuntimeData | None]


async def _ensure_required_subentries(hass: HomeAssistant, hub_entry: ConfigEntry) -> None:
    """Ensure required subentries exist for the hub.

    Creates a Network subentry (for optimization sensors) if missing.
    In non-advanced mode, also creates a Switchboard junction if missing.
    """
    subentry_types = {subentry.subentry_type for subentry in hub_entry.subentries.values()}
    has_switchboard = any(
        is_element_type(subentry_type) and ELEMENT_TYPES[subentry_type].switchboard for subentry_type in subentry_types
    )
    advanced_mode = hub_entry.data.get(HUB_SECTION_ADVANCED, {}).get(CONF_ADVANCED_MODE, False)

    required: list[ConfigSubentryData] = []
    if ELEMENT_TYPE_NETWORK not in subentry_types:
        required.append(await async_network_subentry(hass))
    if not advanced_mode and not has_switchboard:
        required.append(await async_switchboard_subentry(hass))

    for subentry in required:
        _LOGGER.info("Creating %s subentry for hub %s", subentry["title"], hub_entry.entry_id)
        hass.config_entries.async_add_subentry(
            hub_entry,
            ConfigSubentry(
                data=MappingProxyType(subentry["data"]),
                subentry_type=subentry["subentry_type"],
                title=subentry["title"],
                unique_id=subentry["unique_id"],
            ),
        )


async def async_update_listener(hass: HomeAssistant, entry: HaeoConfigEntry) -> None:
    """Handle options update or subentry changes.

    This listener is called for all config entry changes including subentry
    additions, updates, and removals. Value-only updates (from input entities)
    set value_update_in_progress to skip reload and signal the coordinator.

    Uses async_schedule_reload instead of async_reload to avoid suspending
    in the listener task. Required subentries are ensured during setup, so
    no need to check here.
    """
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

    # Clean up policy rules that reference deleted elements. An element's
    # subentry is committed only after its config flow finishes, but the flow
    # writes the element's surfaced policy rules before that. Skip cleanup while
    # a subentry flow for this entry is active so those rules are not mistaken
    # for orphans; element deletions do not run a flow, so they still clean up.
    flow_in_progress = _element_flow_in_progress(hass, entry)
    if not flow_in_progress:
        prune_element_references(hass, entry)

    _LOGGER.info("HAEO configuration changed, reloading integration")

    if not flow_in_progress:
        hass.config_entries.async_schedule_reload(entry.entry_id)
        return

    # A subentry flow may still be committing further subentries in the same
    # synchronous step: the battery flow writes its surfaced policy rules before
    # creating its own subentry. Home Assistant fires update listeners and runs
    # reloads eagerly, so scheduling the reload now runs the unload phase
    # synchronously from within this change callback, which removes this update
    # listener before the later subentry commit fires it; that commit then never
    # schedules a reload and the new element is left without a device or
    # entities. Defer to the next event loop iteration so every commit in this
    # step lands first, and coalesce the deferred reloads so the flow rebuilds
    # the entry exactly once with all subentries present.
    if runtime_data is None:
        hass.loop.call_soon(hass.config_entries.async_schedule_reload, entry.entry_id)
        return

    if runtime_data.reload_pending:
        return
    runtime_data.reload_pending = True

    def _deferred_reload() -> None:
        # Clear the coalescing flag before scheduling so it cannot stick across
        # synchronous steps; the reload recreates runtime_data regardless.
        runtime_data.reload_pending = False
        hass.config_entries.async_schedule_reload(entry.entry_id)

    hass.loop.call_soon(_deferred_reload)


def _element_flow_in_progress(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Return whether a subentry config flow for this entry is in progress."""
    return any(flow["handler"][0] == entry.entry_id for flow in hass.config_entries.subentries.async_progress())


def prune_element_references(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove references to deleted elements from the elements that name them.

    Each element type that names other elements declares how it drops names
    that no longer exist; an element left with nothing to do is removed.
    """
    subentries = list(entry.subentries.values())
    referencing = [
        (subentry, ELEMENT_REFERENCE_PRUNERS[subentry.subentry_type])
        for subentry in subentries
        if subentry.subentry_type in ELEMENT_REFERENCE_PRUNERS
    ]
    for subentry, prune in referencing:
        element_names = {other.title for other in subentries if other.subentry_id != subentry.subentry_id}
        pruned = prune(subentry.data, element_names)
        if pruned is None:
            hass.config_entries.async_remove_subentry(entry, subentry.subentry_id)
        elif pruned != subentry.data:
            hass.config_entries.async_update_subentry(entry, subentry, data=pruned)


async def _async_first_refresh(
    hass: HomeAssistant,
    entry: HaeoConfigEntry,
    runtime_data: HaeoRuntimeData,
    coordinator: HaeoDataUpdateCoordinator,
) -> None:
    """Wait for every input to be ready, then run the first optimization."""
    # Wait for every input store to have data or to reject its source's value,
    # so a rejected value is reported at once rather than after the timeout
    _LOGGER.debug("Waiting for %d input stores to be ready", len(runtime_data.input_stores))
    try:
        async with asyncio.timeout(INPUT_ENTITY_READY_TIMEOUT):
            await asyncio.gather(*[store.wait_settled() for store in runtime_data.input_stores.values()])
    except TimeoutError:
        raise_for_rejected_input(runtime_data.input_stores, ConfigEntryNotReady)
        not_ready = unavailable_input_sources(runtime_data.input_stores, lambda store: not store.is_ready())
        sync_unavailable_input_issues(hass, entry.entry_id, not_ready)
        key, entities = next(iter(not_ready.items()))
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="input_unavailable",
            translation_placeholders=unavailable_input_placeholders(key, entities),
        ) from None
    raise_for_rejected_input(runtime_data.input_stores, ConfigEntryNotReady)
    _LOGGER.debug("All input entities ready")

    # Wrap coordinator operations to provide meaningful HA error messages
    try:
        # Initialize the network and set up subscriptions
        # This must happen before the first refresh
        await coordinator.async_initialize()

        # Trigger initial optimization before output platform setup so the output
        # sensors can be created with the platform. If it fails, the sensor platform
        # adds them after the first successful optimization instead.
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


async def async_setup_entry(hass: HomeAssistant, entry: HaeoConfigEntry) -> bool:
    """Set up Home Assistant Energy Optimizer from a config entry.

    Uses async_on_unload pattern for cleanup registration. Home Assistant
    automatically calls all registered async_on_unload callbacks when setup
    fails (returns False, raises ConfigEntryNotReady, or raises any exception).

    Forwarded platforms are not covered by those callbacks: async_unload_entry
    unloads them, and any failure or cancellation after the input platforms are
    forwarded unloads those before re-raising.
    """
    # Import here to avoid circular imports at module level
    from custom_components.haeo.entities.device import get_or_create_network_device  # noqa: PLC0415

    # Ensure required subentries exist (auto-create if missing)
    await _ensure_required_subentries(hass, entry)

    # Create network device using centralized device creation
    get_or_create_network_device(hass, entry, network_subentry(entry))

    # Create horizon manager first - input entities and coordinator depend on it
    # This is a pure Python object, not an entity
    horizon_manager = HorizonManager(hass=hass, config_entry=entry)

    # Create runtime data for this setup
    runtime_data = HaeoRuntimeData(horizon_manager=horizon_manager)
    entry.runtime_data = runtime_data

    # Start horizon manager's scheduled updates - returns stop function
    entry.async_on_unload(horizon_manager.start())

    # Build input stores from configuration before any entities exist. The
    # stores are the system's source of truth; entities wrap them for display
    # and the coordinator reads their resolved values.
    runtime_data.input_stores = build_input_stores(hass, entry, horizon_manager)

    # A calendar's state carries no events, so stores reading a calendar are
    # loaded by a loader that fetches its events over the horizon.
    calendar_loader = CalendarInputLoader(hass, entry.entry_id, runtime_data.input_stores, horizon_manager)
    calendar_loader.start()
    entry.async_on_unload(calendar_loader.cleanup)

    # Every other store is loaded from its sources, or its constant, by a loader
    # that follows them and the horizon, so it loads even when its entity is disabled.
    source_loader = SourceInputLoader(hass, runtime_data.input_stores, horizon_manager)
    source_loader.start()
    entry.async_on_unload(source_loader.cleanup)

    # Create the coordinator from the same subentry snapshot used to build the
    # input stores, before setting up platforms. Platform setup and store
    # readiness below yield to the event loop, during which a concurrent
    # subentry commit (which schedules its own reload) can mutate
    # entry.subentries. Capturing the coordinator's participant set now keeps it
    # consistent with the stores it reads from; the pending reload picks up any
    # element added in the meantime.
    coordinator = HaeoDataUpdateCoordinator(hass, entry)
    runtime_data.coordinator = coordinator
    entry.async_on_unload(coordinator.cleanup)

    # Set up input platforms - entities show the prebuilt stores' values.
    await hass.config_entries.async_forward_entry_setups(entry, INPUT_PLATFORMS)
    try:
        await _async_first_refresh(hass, entry, runtime_data, coordinator)
        # Set up output platforms after coordinator has data
        await hass.config_entries.async_forward_entry_setups(entry, OUTPUT_PLATFORMS)
    except BaseException:
        await hass.config_entries.async_unload_platforms(entry, INPUT_PLATFORMS)
        raise

    # Register update listener LAST - after all setup is complete
    # This prevents reload loops from subentry additions during initial setup
    entry.async_on_unload(entry.add_update_listener(async_update_listener))

    _LOGGER.info("HAEO integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HaeoConfigEntry) -> bool:
    """Unload a config entry.

    Unloads the input and output platforms here; Home Assistant then runs the
    async_on_unload callbacks registered during setup (horizon manager timer,
    calendar loader, coordinator resources, update listener).
    """
    _LOGGER.info("Unloading HAEO integration")
    unloaded = await hass.config_entries.async_unload_platforms(entry, [*INPUT_PLATFORMS, *OUTPUT_PLATFORMS])
    if unloaded:
        entry.runtime_data = None
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: HaeoConfigEntry) -> None:
    """Dismiss the repair issues raised for a removed config entry."""
    await async_dismiss_entry_issues(hass, entry.entry_id)


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

    # Check if this device's identifier matches a device of a current subentry
    has_haeo_identifier = False
    for domain, identifier in device_entry.identifiers:
        if domain != DOMAIN:
            continue
        has_haeo_identifier = True

        # Hub device has identifier (DOMAIN, entry_id) without subentry suffix - always keep
        if identifier == config_entry.entry_id:
            return False

        element = parse_element_unique_id(config_entry.entry_id, identifier)
        if element is None or element.subentry_id not in config_entry.subentries:
            continue
        allowed_device_names = ELEMENT_DEVICE_NAMES_BY_TYPE.get(
            config_entry.subentries[element.subentry_id].subentry_type
        )
        # Keep devices of unknown subentry types to avoid accidental removal, and
        # devices still created for their subentry
        if allowed_device_names is None or element.key in allowed_device_names:
            return False

    # If device has no HAEO identifiers, it's not managed by us - keep it
    if not has_haeo_identifier:
        return False

    # Device doesn't match any current subentry or device name - allow removal
    _LOGGER.info(
        "Removing stale device %s (no longer created by this entry)",
        device_entry.name,
    )
    return True
