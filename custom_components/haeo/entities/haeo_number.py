"""Input number entity for HAEO runtime configuration."""

import logging
from typing import Any

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import EventStateChangedData, async_track_state_change_event

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.schema.input_fields import InputFieldInfo

from .mode import ConfigEntityMode

_LOGGER = logging.getLogger(__name__)


class HaeoInputNumber(RestoreNumber):
    """Number entity for HAEO input configuration.

    Created directly from subentry configuration during platform setup.
    Does not require coordinator to exist.

    Supports two modes:
    - Editable: User controls the value, persisted with RestoreNumber
    - Driven: Mirrors an external entity's value
    """

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        subentry: ConfigSubentry,
        field_info: InputFieldInfo,
        device_id: str,
    ) -> None:
        """Initialize the input number entity.

        Args:
            hass: Home Assistant instance
            config_entry: Parent config entry
            subentry: Element subentry containing configuration
            field_info: Metadata about this input field
            device_id: Device identifier for grouping entities

        """
        self.hass = hass
        self._config_entry = config_entry
        self._subentry = subentry
        self._field_info = field_info
        self._field_name = field_info.field_name
        self._element_type = subentry.subentry_type
        self._element_name = subentry.title

        # Determine mode from config value
        config_value = subentry.data.get(self._field_name)
        self._source_entity_id: str | None = None

        if isinstance(config_value, str) and "." in config_value:
            # Looks like an entity ID - Driven mode
            self._entity_mode = ConfigEntityMode.DRIVEN
            self._source_entity_id = config_value
            self._attr_native_value = None
        else:
            # Static value or missing - Editable mode
            self._entity_mode = ConfigEntityMode.EDITABLE
            if config_value is not None and isinstance(config_value, (int, float)):
                self._attr_native_value = float(config_value)

        # Entity attributes
        self._attr_unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_{field_info.field_name}"
        self._attr_translation_key = field_info.translation_key
        self._attr_translation_placeholders = {k: str(v) for k, v in subentry.data.items()}

        # Device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{config_entry.entry_id}_{device_id}")},
        )

        # Number-specific attributes from field metadata
        self._attr_native_unit_of_measurement = field_info.unit
        if field_info.min_value is not None:
            self._attr_native_min_value = field_info.min_value
        if field_info.max_value is not None:
            self._attr_native_max_value = field_info.max_value
        if field_info.step is not None:
            self._attr_native_step = field_info.step

        if field_info.device_class is not None:
            self._attr_device_class = field_info.device_class

        # Unsubscribe callback for Driven mode
        self._unsub_state_change: Any = None

        # Set extra state attributes
        self._update_extra_attributes()

    @property
    def entity_mode(self) -> ConfigEntityMode:
        """Return the current entity mode."""
        return self._entity_mode

    def _update_extra_attributes(self, *, forecast: list[dict[str, Any]] | None = None) -> None:
        """Update extra state attributes.

        Args:
            forecast: Forecast data to include in attributes (from source entity in Driven mode)

        """
        attrs: dict[str, Any] = {
            "entity_mode": self._entity_mode.value,
            "element_name": self._element_name,
            "element_type": self._element_type,
            "field_name": self._field_name,
        }
        if self._source_entity_id:
            attrs["source_entity"] = self._source_entity_id
        if forecast is not None:
            attrs["forecast"] = forecast
        self._attr_extra_state_attributes = attrs

    async def async_added_to_hass(self) -> None:
        """Handle entity being added to Home Assistant."""
        await super().async_added_to_hass()

        if self._entity_mode == ConfigEntityMode.EDITABLE:
            # Restore previous value if available
            last_data = await self.async_get_last_number_data()
            if last_data is not None and last_data.native_value is not None:
                self._attr_native_value = last_data.native_value
        elif self._entity_mode == ConfigEntityMode.DRIVEN and self._source_entity_id:
            # Subscribe to source entity changes
            self._unsub_state_change = async_track_state_change_event(
                self.hass,
                [self._source_entity_id],
                self._handle_source_state_change,
            )
            # Get initial value from source
            self._update_from_source()

    async def async_will_remove_from_hass(self) -> None:
        """Handle entity being removed from Home Assistant."""
        await super().async_will_remove_from_hass()

        if self._unsub_state_change:
            self._unsub_state_change()
            self._unsub_state_change = None

    @callback
    def _handle_source_state_change(self, _event: Event[EventStateChangedData]) -> None:
        """Handle state change of source entity in Driven mode."""
        self._update_from_source()
        self.async_write_ha_state()

    @callback
    def _update_from_source(self) -> None:
        """Update value from source entity."""
        if not self._source_entity_id:
            return

        state = self.hass.states.get(self._source_entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            self._attr_native_value = None
            # Clear forecast when source unavailable
            self._update_extra_attributes(forecast=None)
            return

        try:
            self._attr_native_value = float(state.state)
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Cannot convert source entity %s state '%s' to float",
                self._source_entity_id,
                state.state,
            )
            self._attr_native_value = None

        # Copy forecast from source entity if available
        forecast = state.attributes.get("forecast")
        self._update_extra_attributes(forecast=forecast)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value.

        In Editable mode: stores the value and triggers coordinator refresh.
        In Driven mode: ignored - value is controlled by source entity.
        """
        if self._entity_mode == ConfigEntityMode.DRIVEN:
            _LOGGER.debug("Ignoring set_value in Driven mode for %s", self.entity_id)
            return

        self._attr_native_value = value
        self.async_write_ha_state()

        # Trigger coordinator refresh if available
        coordinator = getattr(self._config_entry, "runtime_data", None)
        if coordinator is not None:
            await coordinator.async_request_refresh()

    def get_current_value(self) -> float | None:
        """Return the current value for use by the optimizer.

        This is called by the coordinator when loading input values.
        """
        return self._attr_native_value


__all__ = ["HaeoInputNumber"]
