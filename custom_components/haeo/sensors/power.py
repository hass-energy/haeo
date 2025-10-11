"""Power sensor for HAEO elements."""

import logging
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower

from custom_components.haeo.const import ATTR_POWER
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.sensors.base import HaeoSensorBase
from custom_components.haeo.sensors.types import DataSource

_LOGGER = logging.getLogger(__name__)


class HaeoPowerSensor(HaeoSensorBase):
    """Generic power sensor that can read from different data sources."""

    def __init__(
        self,
        coordinator: HaeoDataUpdateCoordinator,
        config_entry: ConfigEntry,
        element_name: str,
        element_type: str,
        data_source: DataSource = DataSource.OPTIMIZED,
        translation_key: str = "power",
        name_suffix: str | None = None,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: The data update coordinator
            config_entry: The config entry
            element_name: Name of the element
            element_type: Type of the element
            data_source: Where to get the data from
            translation_key: Translation key for the sensor name
            name_suffix: Optional name suffix (defaults to translation_key)

        """
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
        self.data_source = data_source
        self._attr_translation_key = translation_key
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the current power value."""
        try:
            if self.data_source == DataSource.OPTIMIZED:
                element_data = self.coordinator.get_element_data(self.element_name)
                if element_data and ATTR_POWER in element_data:
                    power_data = element_data[ATTR_POWER]
                    return power_data[0] if power_data else None

            elif self.data_source == DataSource.FORECAST:
                if self.coordinator.network and self.element_name in self.coordinator.network.elements:
                    element = self.coordinator.network.elements[self.element_name]
                    if hasattr(element, "forecast") and element.forecast is not None:
                        return float(element.forecast[0]) if element.forecast else None

        except Exception as ex:
            _LOGGER.debug("Error getting power data for %s: %s", self.element_name, ex)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}

        # Add element metadata
        attrs["element_type"] = self.element_type
        attrs["data_source"] = self.data_source.value

        # Get data based on source
        try:
            power_data = None

            if self.data_source == DataSource.OPTIMIZED:
                element_data = self.coordinator.get_element_data(self.element_name)
                if element_data and ATTR_POWER in element_data:
                    power_data = element_data[ATTR_POWER]

            elif self.data_source == DataSource.FORECAST:
                if self.coordinator.network and self.element_name in self.coordinator.network.elements:
                    element = self.coordinator.network.elements[self.element_name]
                    if hasattr(element, "forecast") and element.forecast is not None:
                        power_data = [float(v) for v in element.forecast]

            if power_data:
                # Add forecast data
                attrs["forecast"] = power_data

                # Add timestamped forecast
                try:
                    timestamps = self.coordinator.get_future_timestamps()
                    if len(timestamps) == len(power_data):
                        attrs["timestamped_forecast"] = [
                            {"timestamp": ts, "value": value} for ts, value in zip(timestamps, power_data, strict=False)
                        ]
                except Exception as ex:
                    _LOGGER.debug("Error getting timestamps for %s: %s", self.element_name, ex)

        except Exception as ex:
            _LOGGER.debug("Error getting power attributes for %s: %s", self.element_name, ex)

        return attrs
