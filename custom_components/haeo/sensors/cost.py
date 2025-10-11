"""Cost sensor for HAEO elements."""

import logging
from typing import Any

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

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        try:
            # For network-level cost sensor, include optimization metadata
            if self.element_type == ELEMENT_TYPE_NETWORK:
                attrs: dict[str, Any] = {}
                if self.coordinator.last_optimization_time:
                    attrs["last_optimization"] = self.coordinator.last_optimization_time.isoformat()
                attrs["optimization_status"] = self.coordinator.optimization_status
                if self.coordinator.last_optimization_duration is not None:
                    attrs["last_duration_seconds"] = self.coordinator.last_optimization_duration
                return attrs if attrs else None

            return None
        except Exception:
            _LOGGER.exception("Error getting extra state attributes for cost sensor %s", self.element_name)
            return None
