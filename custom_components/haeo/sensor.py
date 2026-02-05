"""Sensor platform for Home Assistant Energy Optimizer integration."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import ELEMENT_TYPE_NETWORK
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
    entities: list[SensorEntity] = [horizon_entity]

    # Create sensors for each output in the coordinator data grouped by element
    if coordinator.data:
        for subentry in config_entry.subentries.values():
            # Get all devices under this subentry (may be multiple, e.g., battery regions)
            subentry_devices = coordinator.data.get(subentry.title, {})

            # Pass subentry data as translation placeholders (convert all values to strings)
            translation_placeholders = {k: str(v) for k, v in subentry.data.items()}

            for device_name, device_outputs in subentry_devices.items():
                # Get or create the device using centralized device creation
                device_entry = get_or_create_element_device(hass, config_entry, subentry, device_name)

                # Build unique ID using consistent identifier pattern
                device_identifier = build_device_identifier(config_entry, subentry, device_name)

                for output_name, output_data in device_outputs.items():
                    entities.append(
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
                    )

    if entities:
        async_add_entities(entities)
    else:
        _LOGGER.debug("No sensors created for entry %s", config_entry.entry_id)


__all__ = ["async_setup_entry"]
