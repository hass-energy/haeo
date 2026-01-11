"""Sensor platform for Home Assistant Energy Optimizer integration."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import DOMAIN, ELEMENT_TYPE_NETWORK
from custom_components.haeo.entities import HaeoSensor
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

    # Get the device registry
    dr = device_registry.async_get(hass)

    # Find network subentry for horizon entity's device
    network_subentry = next(
        (s for s in config_entry.subentries.values() if s.subentry_type == ELEMENT_TYPE_NETWORK),
        None,
    )
    if network_subentry is None:
        msg = "No network subentry found - integration setup incomplete"
        raise RuntimeError(msg)

    # Get the network device (created in __init__.py)
    network_device_entry = dr.async_get_or_create(
        identifiers={(DOMAIN, f"{config_entry.entry_id}_{network_subentry.subentry_id}_{ELEMENT_TYPE_NETWORK}")},
        config_entry_id=config_entry.entry_id,
        config_subentry_id=network_subentry.subentry_id,
        translation_key=ELEMENT_TYPE_NETWORK,
        translation_placeholders={"name": network_subentry.title},
    )

    # Create horizon entity that displays horizon manager state
    horizon_entity = HaeoHorizonEntity(
        hass=hass,
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
                # Create a unique device identifier matching number.py and switch.py format:
                # {entry_id}_{subentry_id}_{device_name}
                # For main devices, device_name == subentry_type (e.g., "battery")
                # For sub-devices, device_name differs (e.g., "battery_device_normal")
                device_id_suffix = f"{subentry.subentry_id}_{device_name}"

                # Get or create the device for this element
                # Device name is already constrained to ElementDeviceName type, so use it directly as translation key
                device_entry = dr.async_get_or_create(
                    identifiers={(DOMAIN, f"{config_entry.entry_id}_{device_id_suffix}")},
                    config_entry_id=config_entry.entry_id,
                    config_subentry_id=subentry.subentry_id,
                    translation_key=device_name,
                    translation_placeholders={"name": subentry.title},
                )

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

    if entities:
        async_add_entities(entities)
    else:
        _LOGGER.debug("No sensors created for entry %s", config_entry.entry_id)


__all__ = ["async_setup_entry"]
