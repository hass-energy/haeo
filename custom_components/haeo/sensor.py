"""Sensor platform for Home Assistant Energy Optimizer integration."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import ELEMENT_TYPE_NETWORK, OUTPUT_NAME_OPTIMIZATION_STATUS
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.entities import HaeoSensor
from custom_components.haeo.entities.device import (
    build_device_identifier,
    get_or_create_element_device,
    get_or_create_network_device,
)
from custom_components.haeo.entities.haeo_horizon import HaeoHorizonEntity
from custom_components.haeo.entities.haeo_status import HaeoStatusSensor
from custom_components.haeo.entities.translation_placeholders import build_translation_placeholders

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
    status_entity = HaeoStatusSensor(
        coordinator,
        device_entry=network_device_entry,
        network_subentry=network_subentry,
        unique_id=(
            f"{build_device_identifier(config_entry, network_subentry, ELEMENT_TYPE_NETWORK)[1]}"
            f"_{OUTPUT_NAME_OPTIMIZATION_STATUS}"
        ),
    )
    # Output sensors are built from the coordinator's outputs. If the first optimization
    # after a load or reload failed there are none yet, so they are added on the first
    # successful update instead.
    if coordinator.data:
        async_add_entities([horizon_entity, status_entity, *_build_output_entities(hass, config_entry, coordinator)])
        return

    async_add_entities([horizon_entity, status_entity])
    added = False

    @callback
    def _add_when_ready() -> None:
        nonlocal added
        # An update can finish while the entry is unloading, when entities must not be added
        if added or not coordinator.data or config_entry.state is not ConfigEntryState.LOADED:
            return
        added = True
        async_add_entities(_build_output_entities(hass, config_entry, coordinator))

    config_entry.async_on_unload(coordinator.async_add_listener(_add_when_ready))


def _build_output_entities(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    coordinator: HaeoDataUpdateCoordinator,
) -> list[SensorEntity]:
    """Build one sensor per output of the coordinator's latest data, grouped by element."""
    entities: list[SensorEntity] = []
    for subentry in config_entry.subentries.values():
        # Get all devices under this subentry (may be multiple, e.g., battery regions)
        subentry_devices = coordinator.data.outputs.get(subentry.title, {})

        translation_placeholders = build_translation_placeholders(subentry)

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
