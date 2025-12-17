"""Sensor platform for Home Assistant Energy Optimizer integration.

This module serves as the entry point for the sensor platform.
"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo.entities import EntityPlatform, async_setup_platform_entities
from custom_components.haeo.entities.haeo_sensor import HaeoSensor

# Sensors are read-only and use coordinator, so unlimited parallel updates is safe
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAEO sensor entities."""
    await async_setup_platform_entities(
        hass,
        config_entry,
        async_add_entities,
        EntityPlatform.SENSOR,
        HaeoSensor,
    )


__all__ = ["async_setup_entry"]
