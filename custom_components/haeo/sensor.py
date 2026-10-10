"""Sensor platform for Home Assistant Energy Optimizer integration."""

from collections.abc import Callable
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import ELEMENT_TYPE_NETWORK
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.entities import HaeoSensor
from custom_components.haeo.entities.device import (
    build_device_identifier,
    get_or_create_element_device,
    get_or_create_network_device,
)
from custom_components.haeo.entities.haeo_horizon import HaeoHorizonEntity

_LOGGER = logging.getLogger(__name__)

# Sensors are read-only and use coordinator, so unlimited parallel updates is safe
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAEO sensor entities."""
    # Runtime data must be set by __init__.py before platforms are set up
    runtime_data: HaeoRuntimeData | None = getattr(config_entry, "runtime_data", None)
    if runtime_data is None:
        msg = "Runtime data not set - integration setup incomplete"
        raise RuntimeError(msg)

    coordinator = runtime_data.coordinator
    if coordinator is None:
        msg = "Coordinator not set - integration setup incomplete"
        raise RuntimeError(msg)

    horizon_manager = runtime_data.horizon_manager

    # Find network subentry for horizon entity's device
    network_subentry = next(
        (s for s in config_entry.subentries.values() if s.subentry_type == ELEMENT_TYPE_NETWORK),
        None,
    )
    if network_subentry is None:
        msg = "No network subentry found - integration setup incomplete"
        raise RuntimeError(msg)

    # Get the network device using centralized device creation
    network_device_entry = get_or_create_network_device(hass, config_entry, network_subentry)

    # Create horizon entity that displays horizon manager state
    horizon_entity = HaeoHorizonEntity(
        config_entry=config_entry,
        device_entry=network_device_entry,
        horizon_manager=horizon_manager,
    )
    # Output sensors can only be built once the coordinator has produced data. If the
    # first optimisation after (re)load failed, data is still None here, so defer them
    # to the first successful update rather than leaving the entry without outputs.
    # DataUpdateCoordinator types `data` as non-optional, but it really is None until
    # the first successful refresh, so this has to be a truthiness check.
    if not coordinator.data:
        async_add_entities([horizon_entity])
        _LOGGER.debug(
            "No optimization data yet for entry %s; deferring output sensors to the first successful update",
            config_entry.entry_id,
        )
        _defer_output_sensors(hass, config_entry, coordinator, async_add_entities)
        return

    async_add_entities([horizon_entity, *_build_output_entities(hass, config_entry, coordinator)])


def _defer_output_sensors(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    coordinator: HaeoDataUpdateCoordinator,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the output sensors once the coordinator first produces data.

    The listener removes itself after a successful update so later refreshes do not
    create duplicate entities.
    """
    remove_listener: Callable[[], None] | None = None

    @callback
    def _add_when_ready() -> None:
        nonlocal remove_listener

        if not coordinator.data:
            return

        if remove_listener is not None:
            remove_listener()
            remove_listener = None

        _LOGGER.debug("Creating deferred output sensors for entry %s", config_entry.entry_id)
        async_add_entities(_build_output_entities(hass, config_entry, coordinator))

    remove_listener = coordinator.async_add_listener(_add_when_ready)

    @callback
    def _cleanup() -> None:
        """Drop the listener if the entry unloads before any successful update."""
        if remove_listener is not None:
            remove_listener()

    config_entry.async_on_unload(_cleanup)


def _build_output_entities(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    coordinator: HaeoDataUpdateCoordinator,
) -> list[SensorEntity]:
    """Build one sensor per coordinator output, grouped by element."""
    data = coordinator.data
    if not data:
        return []

    entities: list[SensorEntity] = []
    for subentry in config_entry.subentries.values():
        # Get all devices under this subentry (may be multiple, e.g., battery regions)
        subentry_devices = data.outputs.get(subentry.title, {})

        # Pass subentry data as translation placeholders (convert all values to strings)
        translation_placeholders = {k: str(v) for k, v in subentry.data.items()}

        for device_name, device_outputs in subentry_devices.items():
            # Get or create the device using centralized device creation
            device_entry = get_or_create_element_device(hass, config_entry, subentry, device_name)

            # Build unique ID using consistent identifier pattern
            device_identifier = build_device_identifier(config_entry, subentry, device_name)

            entities.extend(
                HaeoSensor(
                    coordinator,
                    device_entry=device_entry,
                    subentry_key=subentry.title,
                    device_key=device_name,
                    element_title=subentry.title,
                    element_type=subentry.subentry_type,
                    output_name=output_name,
                    output_data=output_data,
                    unique_id=f"{device_identifier[1]}_{output_name}",
                    translation_placeholders=translation_placeholders,
                )
                for output_name, output_data in device_outputs.items()
            )

    return entities


__all__ = ["async_setup_entry"]
