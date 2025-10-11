"""Cost sensor for HAEO elements."""

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_DOLLAR

from custom_components.haeo.const import ELEMENT_TYPE_NETWORK
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.sensors.base import HaeoSensorBase

_LOGGER = logging.getLogger(__name__)


class HaeoCostSensor(HaeoSensorBase):
    """Generic cost sensor."""

    def __init__(
        self,
        coordinator: HaeoDataUpdateCoordinator,
        config_entry: ConfigEntry,
        element_name: str,
        element_type: str,
        translation_key: str = "cost",
        name_suffix: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        suffix = name_suffix or "Cost"
        sensor_id = f"{element_name}_cost"

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
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = CURRENCY_DOLLAR  # Default fallback
        self._attr_state_class = SensorStateClass.TOTAL

    async def async_added_to_hass(self) -> None:
        """Set up the sensor when added to hass."""
        await super().async_added_to_hass()
        # Update unit of measurement to use the user's configured currency
        if self.hass and self.hass.config.currency:
            self._attr_native_unit_of_measurement = self.hass.config.currency

    @property
    def native_value(self) -> float | None:
        """Return the cost value."""
        # For network-level cost (optimization cost), get from coordinator
        if self.element_type == ELEMENT_TYPE_NETWORK:
            return self.coordinator.last_optimization_cost

        # For element-specific cost, would get from element data
        # This can be extended in the future
        return None
