"""Base sensor classes for HAEO integration."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigSubentry
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.haeo.const import ELEMENT_TYPE_NETWORK, OPTIMIZATION_STATUS_PENDING
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class HaeoSensorBase(CoordinatorEntity[HaeoDataUpdateCoordinator], SensorEntity):
    """Base class for HAEO sensors."""

    coordinator: HaeoDataUpdateCoordinator
    element_name: str
    element_type: str

    def __init__(
        self,
        coordinator: HaeoDataUpdateCoordinator,
        subentry: ConfigSubentry,
        sensor_type: str,
        name_suffix: str,
        element_name: str,
        element_type: str,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        # Verify coordinator has config_entry
        if not coordinator.config_entry:
            msg = "Coordinator must have a config_entry"
            raise ValueError(msg)

        self.coordinator = coordinator
        self.subentry = subentry
        self.sensor_type = sensor_type
        self.element_name = element_name
        self.element_type = element_type
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{subentry.subentry_id}_{sensor_type}"
        self._attr_translation_key = element_type or sensor_type

        # Set sensor name with HAEO prefix
        # Check if name_suffix already contains the element name to avoid duplication
        if element_name in name_suffix:
            self._attr_name = f"HAEO {name_suffix}"
        else:
            self._attr_name = f"HAEO {element_name} {name_suffix}"

        # Link directly to the pre-created device by fetching it from the device registry
        # This ensures proper subentry association without relying on device_info matching
        device_reg = dr.async_get(coordinator.hass)
        self.device_entry = device_reg.async_get(device_id)

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        # Check if coordinator is available
        if not super().available:
            return False

        # For element-specific sensors (not network-level), check if we can get element data
        if self.element_type != ELEMENT_TYPE_NETWORK:
            try:
                element_data = self.coordinator.get_element_data(self.element_name)
            except Exception:
                return False

            return element_data is not None

        # For network-level sensors (cost, status), check if coordinator has optimization results
        if self.element_type == ELEMENT_TYPE_NETWORK:
            return (
                self.coordinator.optimization_result is not None
                or self.coordinator.optimization_status != OPTIMIZATION_STATUS_PENDING
            )

        return True
