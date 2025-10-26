"""Sensor platform for Home Assistant Energy Optimization integration."""

import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

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
    _hass: HomeAssistant,
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

    if coordinator.data:
        for element_name, outputs in coordinator.data.items():
            if not outputs:
                continue

            element_key = slugify(element_name) if element_name != "network" else "network"
            for output_name, output_data in outputs.items():
                unique_id = f"{config_entry.entry_id}_{element_key}_{output_name}"

                entities.append(
                    HaeoSensor(
                        coordinator,
                        element_name=element_name,
                        output_name=output_name,
                        output_data=output_data,
                        unique_id=unique_id,
                    )
                )

    if entities:
        async_add_entities(entities)
    else:
        _LOGGER.debug("No sensors created for entry %s", config_entry.entry_id)


__all__ = ["HaeoSensor", "async_setup_entry"]
