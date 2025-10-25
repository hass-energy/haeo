"""Sensor platform for Home Assistant Energy Optimization integration."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.elements import get_model_description, is_element_config_schema
from custom_components.haeo.sensors.element import (
    SENSOR_TYPE_AVAILABLE_POWER,
    SENSOR_TYPE_ENERGY,
    SENSOR_TYPE_OPTIMIZATION_COST,
    SENSOR_TYPE_OPTIMIZATION_DURATION,
    SENSOR_TYPE_OPTIMIZATION_STATUS,
    SENSOR_TYPE_POWER,
    SENSOR_TYPE_SOC,
    HaeoElementSensor,
)

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES: tuple[str, ...] = (
    SENSOR_TYPE_OPTIMIZATION_COST,
    SENSOR_TYPE_OPTIMIZATION_STATUS,
    SENSOR_TYPE_OPTIMIZATION_DURATION,
    SENSOR_TYPE_POWER,
    SENSOR_TYPE_AVAILABLE_POWER,
    SENSOR_TYPE_ENERGY,
    SENSOR_TYPE_SOC,
)


async def async_register_devices(hass: HomeAssistant, config_entry: ConfigEntry) -> dict[str, str]:
    """Register devices for validated subentries and return their IDs."""

    device_registry_client = device_registry.async_get(hass)
    device_ids: dict[str, str] = {}

    for subentry in config_entry.subentries.values():
        if subentry.subentry_type == "network" and not is_element_config_schema(subentry.data):
            model_description = subentry.subentry_type
        elif is_element_config_schema(subentry.data):
            model_description = get_model_description(subentry.data)
        else:
            msg = f"Cannot determine model description for subentry {subentry.title}"
            raise ValueError(msg)
        device_ids[subentry.title] = device_registry_client.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            config_subentry_id=subentry.subentry_id,
            identifiers={(DOMAIN, f"{config_entry.entry_id}_{subentry.title}")},
            name=subentry.title,
            manufacturer="HAEO",
            model=model_description,
        ).id

    return device_ids


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAEO sensor platform."""

    coordinator: HaeoDataUpdateCoordinator | None = getattr(config_entry, "runtime_data", None)
    if coordinator is None:
        _LOGGER.debug("No coordinator available, skipping sensor setup")
        return

    device_ids = await async_register_devices(hass, config_entry)

    entities: list[SensorEntity] = []

    for subentry in config_entry.subentries.values():
        entities.extend(
            HaeoElementSensor.from_output(
                coordinator,
                element_name=ELEMENT_TYPE_NETWORK,
                element_type=ELEMENT_TYPE_NETWORK,
                device_id=network_device_id,
                output_name=output_name,
                output_data=output_data,
            )
            for output in coordinator.get_element_outputs(subentry.title)
        )

    if entities:
        async_add_entities(entities)
