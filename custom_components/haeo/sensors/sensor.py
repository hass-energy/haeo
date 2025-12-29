"""Simplified sensor implementation for HAEO outputs."""

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.haeo.coordinator_network import CoordinatorOutput, HaeoDataUpdateCoordinator
from custom_components.haeo.elements import ElementDeviceName, ElementOutputName
from custom_components.haeo.model import OutputType


class HaeoSensor(CoordinatorEntity[HaeoDataUpdateCoordinator], SensorEntity):
    """Sensor exposing optimization outputs for HAEO elements and network."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HaeoDataUpdateCoordinator,
        device_entry: DeviceEntry,
        *,
        subentry_key: str,
        device_key: ElementDeviceName,
        element_title: str,
        element_type: str,
        output_name: ElementOutputName,
        output_data: CoordinatorOutput,
        unique_id: str,
        translation_placeholders: dict[str, str] | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self.device_entry = device_entry

        self._subentry_key: str = subentry_key
        self._device_key: ElementDeviceName = device_key
        self._element_title: str = element_title
        self._element_type: str = element_type
        self._output_name: ElementOutputName = output_name
        self._output_type: OutputType = output_data.type

        self._attr_translation_key = output_name
        self._attr_unique_id = unique_id
        if translation_placeholders is not None:
            self._attr_translation_placeholders = translation_placeholders
        self._apply_output(output_data)

    @property
    def available(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return if sensor is available based on coordinator success."""
        return super().available and self.coordinator.last_update_success

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updates from the coordinator."""

        attributes: dict[str, Any] = {
            "element_name": self._element_title,
            "element_type": self._element_type,
            "output_name": self._output_name,
            "output_type": self._output_type,
            "advanced": False,
        }
        native_value: StateType | None = None

        # Navigate the nested structure: subentry -> device -> outputs
        subentry_devices = self.coordinator.data.get(self._subentry_key) if self.coordinator.data else None
        outputs = subentry_devices.get(self._device_key) if subentry_devices else None
        if outputs:
            output_data = outputs.get(self._output_name)
            if output_data is not None:
                self._output_type = output_data.type
                attributes["output_type"] = self._output_type
                if output_data.direction is not None:
                    attributes["direction"] = output_data.direction
                attributes["advanced"] = output_data.advanced
                self._apply_output(output_data)
                if output_data.state is not None:
                    native_value = output_data.state

                if output_data.forecast:
                    attributes["forecast"] = list(output_data.forecast)

        self._attr_native_value = native_value
        self._attr_extra_state_attributes = attributes
        super()._handle_coordinator_update()

    async def async_added_to_hass(self) -> None:
        """Finalize setup when entity is added to Home Assistant."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    def _apply_output(self, output: CoordinatorOutput) -> None:
        """Apply device class, options, and unit metadata for an output."""
        self._attr_native_value = output.state
        self._attr_entity_category = output.entity_category
        self._attr_native_unit_of_measurement = output.unit
        self._attr_device_class = output.device_class
        self._attr_state_class = output.state_class
        self._attr_options = list(output.options) if output.options is not None else None


__all__ = ["HaeoSensor"]
