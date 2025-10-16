"""State of Charge sensor for HAEO battery elements."""

import logging
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry

from custom_components.haeo.const import ATTR_ENERGY
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.sensors.base import HaeoSensorBase

_LOGGER = logging.getLogger(__name__)


class HaeoSOCSensor(HaeoSensorBase):
    """Generic state of charge sensor for batteries."""

    def __init__(
        self,
        coordinator: HaeoDataUpdateCoordinator,
        config_entry: ConfigEntry,
        element_name: str,
        element_type: str,
        translation_key: str = "soc",
        name_suffix: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        suffix = name_suffix or "State of Charge"
        sensor_id = f"{element_name}_state_of_charge"

        super().__init__(
            coordinator,
            config_entry,
            sensor_id,
            f"{element_name} {suffix}",
            element_name,
            element_type,
        )
        self.element_name = element_name
        self._attr_translation_key = translation_key
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_native_unit_of_measurement = "%"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the current state of charge percentage."""
        try:
            element_data = self.coordinator.get_element_data(self.element_name)
            if (
                element_data
                and ATTR_ENERGY in element_data
                and self.coordinator.network
                and self.element_name in self.coordinator.network.elements
            ):
                element = self.coordinator.network.elements[self.element_name]
                if hasattr(element, "capacity"):
                    energy_data = element_data[ATTR_ENERGY]
                    if energy_data and element.capacity > 0:
                        return float((energy_data[0] / element.capacity) * 100.0)
        except Exception as ex:
            _LOGGER.debug("Error getting SOC for %s: %s", self.element_name, ex)
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
            if (
                element_data
                and ATTR_ENERGY in element_data
                and self.coordinator.network
                and self.element_name in self.coordinator.network.elements
            ):
                element = self.coordinator.network.elements[self.element_name]
                if hasattr(element, "capacity") and element.capacity > 0:
                    energy_data = element_data[ATTR_ENERGY]

                    # Convert energy values to SOC percentages
                    soc_data = [(energy / element.capacity) * 100.0 for energy in energy_data]

                    # Add timestamped forecast as dictionary
                    attrs["capacity"] = element.capacity
                    try:
                        timestamps = self.coordinator.get_future_timestamps()
                        if len(timestamps) == len(soc_data):
                            attrs["forecast"] = dict(zip(timestamps, soc_data, strict=False))
                    except Exception as ex:
                        _LOGGER.debug("Error getting timestamps for %s: %s", self.element_name, ex)
        except Exception as ex:
            _LOGGER.debug("Error getting SOC attributes for %s: %s", self.element_name, ex)
        return attrs
