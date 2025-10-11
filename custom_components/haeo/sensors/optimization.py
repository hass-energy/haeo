"""Optimization-level sensors for HAEO integration."""

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime

from custom_components.haeo.const import ELEMENT_TYPE_NETWORK, OPTIMIZATION_STATUS_SUCCESS
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.sensors.base import HaeoSensorBase
from custom_components.haeo.sensors.cost import HaeoCostSensor


class HaeoOptimizationCostSensor(HaeoCostSensor):
    """Sensor for optimization cost (network-level cost sensor)."""

    def __init__(
        self,
        coordinator: HaeoDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            config_entry,
            "network",
            ELEMENT_TYPE_NETWORK,
            translation_key="optimization_cost",
            name_suffix="Optimization Cost",
        )


class HaeoOptimizationStatusSensor(HaeoSensorBase):
    """Sensor for optimization status."""

    def __init__(
        self,
        coordinator: HaeoDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator, config_entry, "optimization_status", "Optimization Status", "network", ELEMENT_TYPE_NETWORK
        )
        self._attr_translation_key = "optimization_status"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        return self.coordinator.optimization_status

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        if self.coordinator.optimization_status == OPTIMIZATION_STATUS_SUCCESS:
            return "mdi:check-circle"
        return "mdi:alert-circle"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}
        if self.coordinator.last_optimization_time:
            attrs["last_optimization"] = self.coordinator.last_optimization_time.isoformat()
        if self.coordinator.last_optimization_cost is not None:
            attrs["last_cost"] = self.coordinator.last_optimization_cost
        if self.coordinator.last_optimization_duration is not None:
            attrs["last_duration_seconds"] = self.coordinator.last_optimization_duration
        return attrs


class HaeoOptimizationDurationSensor(HaeoSensorBase):
    """Sensor for optimization duration."""

    def __init__(
        self,
        coordinator: HaeoDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator, config_entry, "optimization_duration", "Optimization Duration", "network", ELEMENT_TYPE_NETWORK
        )
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_translation_key = "optimization_duration"

    @property
    def native_value(self) -> float | None:
        """Return the optimization duration in seconds."""
        return self.coordinator.last_optimization_duration

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        attrs = {}
        if self.coordinator.last_optimization_time:
            attrs["last_optimization"] = self.coordinator.last_optimization_time.isoformat()
        attrs["optimization_status"] = self.coordinator.optimization_status
        return attrs
