"""Simplified sensor implementation for HAEO outputs."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.haeo.coordinator import CoordinatorOutput, HaeoDataUpdateCoordinator
from custom_components.haeo.model import OutputName, OutputType


class HaeoSensor(CoordinatorEntity[HaeoDataUpdateCoordinator], SensorEntity):
    """Sensor exposing optimization outputs for HAEO elements and network."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HaeoDataUpdateCoordinator,
        device_entry: DeviceEntry,
        *,
        element_key: str,
        element_title: str,
        element_type: str,
        output_name: OutputName,
        output_data: CoordinatorOutput,
        unique_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self.device_entry = device_entry

        self._element_key: str = element_key
        self._element_title: str = element_title
        self._element_type: str = element_type
        self._output_name: OutputName = output_name
        self._output_type: OutputType = output_data.type

        self._attr_translation_key = output_name
        self._attr_unique_id = unique_id
        self._attr_native_unit_of_measurement = output_data.unit
        self._attr_native_value = output_data.state

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
        }
        native_value: StateType | None = None

        outputs = self.coordinator.data.get(self._element_key) if self.coordinator.data else None
        if outputs:
            output_data = outputs.get(self._output_name)
            if output_data is not None:
                self._output_type = output_data.type
                attributes["output_type"] = self._output_type
                if output_data.state is not None:
                    native_value = output_data.state

                if output_data.forecast:
                    attributes["forecast"] = dict(output_data.forecast)

        self._attr_native_value = native_value
        self._attr_extra_state_attributes = attributes
        super()._handle_coordinator_update()

    async def async_added_to_hass(self) -> None:
        """Finalize setup when entity is added to Home Assistant."""
        await super().async_added_to_hass()
        if self.coordinator.data is not None:
            self._handle_coordinator_update()


__all__ = ["HaeoSensor"]
