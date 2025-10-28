"""Sensor platform for Home Assistant Energy Optimization integration."""

import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.sensors.sensor import HaeoSensor

_LOGGER = logging.getLogger(__name__)

# Sensor type constants for backward compatibility with tests
SENSOR_TYPE_ENERGY: Final = "energy"
SENSOR_TYPE_POWER: Final = "power"
SENSOR_TYPE_SOC: Final = "soc"
SENSOR_TYPE_OPTIMIZATION_COST: Final = "optimization_cost"
SENSOR_TYPE_OPTIMIZATION_STATUS: Final = "optimization_status"
SENSOR_TYPE_OPTIMIZATION_DURATION: Final = "optimization_duration"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAEO sensor entities."""

    coordinator: HaeoDataUpdateCoordinator | None = getattr(config_entry, "runtime_data", None)
    if coordinator is None:
        _LOGGER.debug("No coordinator available, skipping sensor setup")
        return

    # Create a sensor for each output in the coordinator data grouped by element
    entities: list[HaeoSensor] = []

    # Get the device registry
    dr = device_registry.async_get(hass)

    if coordinator.data:
        for subentry in config_entry.subentries.values():
            outputs = coordinator.data.get(subentry.title, {})

            # Get or create the device for this element
            device_entry = dr.async_get_or_create(
                identifiers={(DOMAIN, f"{config_entry.entry_id}_{subentry.subentry_id}")},
                config_entry_id=config_entry.entry_id,
                config_subentry_id=subentry.subentry_id,
                translation_key=subentry.subentry_type,
                translation_placeholders=subentry.data,
            )

            for output_name, output_data in outputs.items():
                entities.append(
                    HaeoSensor(
                        coordinator,
                        device_entry=device_entry,
                        element_name=subentry.title,
                        output_name=output_name,
                        output_data=output_data,
                        unique_id=f"{config_entry.entry_id}_{subentry.subentry_id}_{output_name}",
                    )
                )

    if entities:
        async_add_entities(entities)
    else:
        _LOGGER.debug("No sensors created for entry %s", config_entry.entry_id)


__all__ = ["HaeoSensor", "async_setup_entry"]
