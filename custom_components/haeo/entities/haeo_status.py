"""Sensor reporting whether the latest optimization succeeded."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from custom_components.haeo.const import (
    ELEMENT_TYPE_NETWORK,
    OPTIMIZATION_STATUS_FAILED,
    OUTPUT_NAME_OPTIMIZATION_STATUS,
)
from custom_components.haeo.coordinator import STATUS_OPTIONS, HaeoDataUpdateCoordinator
from custom_components.haeo.core.model import OutputType
from custom_components.haeo.entities.haeo_sensor import TOPOLOGY_UNRECORDED_ATTRIBUTES
from custom_components.haeo.entities.plot_metadata import SOURCE_ROLE_KEY, SOURCE_ROLE_OUTPUT


class HaeoStatusSensor(CoordinatorEntity[HaeoDataUpdateCoordinator], SensorEntity):
    """Sensor showing whether the latest optimization is pending, succeeded, or failed.

    It exists from setup and stays available when an optimization fails, so a
    failure is reported instead of every output simply becoming unavailable.
    It also carries the network topology for the frontend card.
    """

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = OUTPUT_NAME_OPTIMIZATION_STATUS
    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(
        self,
        coordinator: HaeoDataUpdateCoordinator,
        device_entry: DeviceEntry,
        network_subentry: ConfigSubentry,
        unique_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.device_entry = device_entry
        self._network_title = network_subentry.title
        self._attr_unique_id = unique_id
        self._attr_options = list(STATUS_OPTIONS)

    @property
    def available(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return True, because the sensor reports failed optimizations rather than hiding them."""
        return True

    @callback
    def _handle_coordinator_update(self) -> None:
        """Show the coordinator's optimization status."""
        status = self.coordinator.optimization_status
        attributes: dict[str, object] = {
            "element_name": self._network_title,
            "element_type": ELEMENT_TYPE_NETWORK,
            "output_name": OUTPUT_NAME_OPTIMIZATION_STATUS,
            "field_type": OutputType.STATUS,
            SOURCE_ROLE_KEY: SOURCE_ROLE_OUTPUT,
            "advanced": False,
            "topology": self.coordinator.topology,
        }
        if self.coordinator.data:
            # UTC keeps last_run stable across CI machines and HA time zones (snapshot tests)
            attributes["last_run"] = dt_util.as_utc(self.coordinator.data.completed_at).isoformat()
        if status == OPTIMIZATION_STATUS_FAILED:
            attributes["error"] = str(self.coordinator.last_exception)
        self._attr_native_value = status
        self._attr_extra_state_attributes = attributes
        super()._handle_coordinator_update()

    async def async_added_to_hass(self) -> None:
        """Show the current status as soon as the sensor is added."""
        await super().async_added_to_hass()
        self._state_info["unrecorded_attributes"] = TOPOLOGY_UNRECORDED_ATTRIBUTES
        self._handle_coordinator_update()


__all__ = ["HaeoStatusSensor"]
