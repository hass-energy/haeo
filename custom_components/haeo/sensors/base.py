"""Base sensor classes for HAEO integration."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.haeo.const import DOMAIN, OPTIMIZATION_STATUS_PENDING
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def get_device_info_for_element(element_name: str, element_type: str, config_entry: ConfigEntry) -> DeviceInfo:
    """Get device info for a specific element."""
    # Use translation key for the model name - Home Assistant will resolve this
    model_translation_key = f"entity.device.{element_type}"

    return DeviceInfo(
        identifiers={(DOMAIN, f"{config_entry.entry_id}_{element_name}")},
        name=element_name,
        manufacturer="HAEO",
        model=model_translation_key,
        via_device=(DOMAIN, config_entry.entry_id),
    )


def get_device_info_for_network(config_entry: ConfigEntry) -> DeviceInfo:
    """Get device info for the main hub."""
    return DeviceInfo(
        identifiers={(DOMAIN, config_entry.entry_id)},
        name="HAEO Network",
        manufacturer="HAEO",
        model="entity.device.network",
        sw_version="1.0.0",
    )


class HaeoSensorBase(CoordinatorEntity[HaeoDataUpdateCoordinator], SensorEntity):
    """Base class for HAEO sensors."""

    coordinator: HaeoDataUpdateCoordinator
    element_name: str
    element_type: str

    def __init__(
        self,
        coordinator: HaeoDataUpdateCoordinator,
        config_entry: ConfigEntry,
        sensor_type: str,
        name_suffix: str,
        element_name: str,
        element_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.sensor_type = sensor_type
        self.element_name = element_name
        self.element_type = element_type
        self._attr_unique_id = f"{config_entry.entry_id}_{sensor_type}"
        self._attr_translation_key = element_type or sensor_type

        # Set sensor name with HAEO prefix
        # Check if name_suffix already contains the element name to avoid duplication
        if element_name in name_suffix:
            self._attr_name = f"HAEO {name_suffix}"
        else:
            self._attr_name = f"HAEO {element_name} {name_suffix}"

        # Set device info based on element type
        if element_type == "network":
            self._attr_device_info = get_device_info_for_network(config_entry)
        else:
            self._attr_device_info = get_device_info_for_element(element_name, element_type, config_entry)

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        # Check if coordinator is available
        if not super().available:
            return False

        # For element-specific sensors (not network-level), check if we can get element data
        if self.element_type != "network":
            try:
                element_data = self.coordinator.get_element_data(self.element_name)
            except Exception:
                return False

            return element_data is not None

        # For hub-level sensors, check if coordinator has optimization results
        if self.sensor_type in ["optimization_cost", "optimization_status"]:
            return (
                self.coordinator.optimization_result is not None
                or self.coordinator.optimization_status != OPTIMIZATION_STATUS_PENDING
            )

        return True

