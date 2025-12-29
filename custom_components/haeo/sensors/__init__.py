"""Sensor platform for Home Assistant Energy Optimizer integration."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import DOMAIN, ELEMENT_TYPE_NETWORK
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.entities.haeo_horizon import HaeoHorizonEntity
from custom_components.haeo.sensors.sensor import HaeoSensor

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAEO sensor entities."""

    runtime_data: HaeoRuntimeData | None = getattr(config_entry, "runtime_data", None)
    if runtime_data is None:
        _LOGGER.debug("No runtime data available, skipping sensor setup")
        return

    coordinator: HaeoDataUpdateCoordinator = runtime_data.network_coordinator

    # Create a sensor for each output in the coordinator data grouped by element
    entities: list[SensorEntity] = []

    # Get the device registry
    dr = device_registry.async_get(hass)

    # Track network device for horizon entity
    network_device_entry = None

    if coordinator.data:
        for subentry in config_entry.subentries.values():
            # Get all devices under this subentry (may be multiple, e.g., battery regions)
            subentry_devices = coordinator.data.get(subentry.title, {})

            # Pass subentry data as translation placeholders (convert all values to strings)
            translation_placeholders = {k: str(v) for k, v in subentry.data.items()}

            for device_name, device_outputs in subentry_devices.items():
                # Create a unique device identifier that includes device name for sub-devices
                is_sub_device = device_name != subentry.title
                device_id_suffix = f"{subentry.subentry_id}_{device_name}" if is_sub_device else subentry.subentry_id

                # Get or create the device for this element
                # Device name is already constrained to ElementDeviceName type, so use it directly as translation key
                device_entry = dr.async_get_or_create(
                    identifiers={(DOMAIN, f"{config_entry.entry_id}_{device_id_suffix}")},
                    config_entry_id=config_entry.entry_id,
                    config_subentry_id=subentry.subentry_id,
                    translation_key=device_name,
                    translation_placeholders={"name": subentry.title},
                )

                # Track network device for horizon entity
                if subentry.subentry_type == ELEMENT_TYPE_NETWORK:
                    network_device_entry = device_entry

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
                            unique_id=f"{config_entry.entry_id}_{device_id_suffix}_{output_name}",
                            translation_placeholders=translation_placeholders,
                        )
                    )

    # Create horizon entity on network device
    if network_device_entry is not None:
        horizon_entity = HaeoHorizonEntity(
            hass=hass,
            config_entry=config_entry,
            device_entry=network_device_entry,
        )
        entities.append(horizon_entity)
        # Store in runtime data for other entities to subscribe
        runtime_data.horizon_entity = horizon_entity

    if entities:
        async_add_entities(entities)
    else:
        _LOGGER.debug("No sensors created for entry %s", config_entry.entry_id)


__all__ = ["HaeoSensor", "async_setup_entry"]
