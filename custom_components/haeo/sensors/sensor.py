"""Simplified sensor implementation for HAEO outputs."""

from __future__ import annotations

from typing import Any, cast

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.haeo.coordinator import CoordinatorOutput, HaeoDataUpdateCoordinator
from custom_components.haeo.model import OUTPUT_NAME_OPTIMIZATION_STATUS, OutputName


class HaeoSensor(CoordinatorEntity[HaeoDataUpdateCoordinator], SensorEntity):
    """Sensor exposing optimization outputs for HAEO elements and network."""

    _attr_should_poll = False

    def __init__(
        self,
        coordinator: HaeoDataUpdateCoordinator,
        *,
        element_name: str,
        output_name: OutputName,
        output_data: CoordinatorOutput,
        unique_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._element_name: str = element_name
        self._output_name: OutputName = output_name

        self._attr_has_entity_name = False
        readable_output = output_name.replace("_", " ").strip().title()
        readable_element = element_name.replace("_", " ").strip().title()
        self._attr_name = f"{readable_element} {readable_output}".strip()
        self._attr_translation_key = output_name
        self._attr_unique_id = unique_id
        self._attr_native_unit_of_measurement = output_data.unit
        if (
            element_name == "network"
            and output_name == OUTPUT_NAME_OPTIMIZATION_STATUS
            and coordinator.optimization_status
        ):
            self._attr_native_value = cast("StateType", coordinator.optimization_status)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updates from the coordinator."""

        attributes: dict[str, Any] = {}
        native_value: StateType | None = None

        outputs = self.coordinator.data.get(self._element_name) if self.coordinator.data else None
        if outputs:
            output_data = outputs.get(self._output_name)
            if output_data is not None:
                if output_data.state is not None:
                    native_value = cast("StateType", output_data.state)

                if output_data.forecast:
                    attributes["forecast"] = dict(output_data.forecast)

        self._attr_native_value = native_value
        self._attr_extra_state_attributes = attributes
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        """Return if sensor is available based on coordinator success."""
        return super().available and self.coordinator.last_update_success


__all__ = ["HaeoSensor"]
