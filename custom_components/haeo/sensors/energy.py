"""Energy sensor for HAEO elements."""

import logging
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy

from custom_components.haeo.const import ATTR_ENERGY
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.sensors.base import HaeoSensorBase

_LOGGER = logging.getLogger(__name__)


class HaeoEnergySensor(HaeoSensorBase):
    """Generic energy sensor for elements with energy storage."""

    def __init__(
        self,
        coordinator: HaeoDataUpdateCoordinator,
        config_entry: ConfigEntry,
        element_name: str,
        element_type: str,
        translation_key: str = "energy",
        name_suffix: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        suffix = name_suffix or translation_key.replace("_", " ").title()
        sensor_id = f"{element_name}_{translation_key}"

        super().__init__(
            coordinator,
            config_entry,
            sensor_id,
            f"{element_name} {suffix}",
            element_name,
            element_type,
        )
        self.element_name = element_name
        self._attr_device_class = SensorDeviceClass.ENERGY_STORAGE
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_translation_key = translation_key

    @property
    def native_value(self) -> float | None:
        """Return the current energy level."""
        try:
            element_data = self.coordinator.get_element_data(self.element_name)
            if element_data and ATTR_ENERGY in element_data:
                energy_data = element_data[ATTR_ENERGY]
                return energy_data[0] if energy_data else None
        except Exception as ex:
            _LOGGER.debug("Error getting energy data for %s: %s", self.element_name, ex)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}

        # Add element metadata
        attrs["element_type"] = self.element_type
        attrs["data_source"] = "optimized"

        try:
            element_data = self.coordinator.get_element_data(self.element_name)
            if element_data and ATTR_ENERGY in element_data:
                energy_data = element_data[ATTR_ENERGY]

                # Add timestamped forecast as dictionary
                try:
                    timestamps = self.coordinator.get_future_timestamps()
                    if len(timestamps) == len(energy_data):
                        attrs["forecast"] = dict(zip(timestamps, energy_data, strict=False))
                except Exception as ex:
                    _LOGGER.debug("Error getting timestamps for %s: %s", self.element_name, ex)
        except Exception as ex:
            _LOGGER.debug("Error getting energy attributes for %s: %s", self.element_name, ex)
        return attrs
