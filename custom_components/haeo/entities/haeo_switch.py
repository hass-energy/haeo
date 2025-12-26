"""Input switch entity for HAEO runtime configuration."""

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntry, DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.schema.input_fields import InputFieldInfo

from .mode import ConfigEntityMode

_LOGGER = logging.getLogger(__name__)


class HaeoInputSwitch(  # pyright: ignore[reportIncompatibleVariableOverride]
    CoordinatorEntity[HaeoDataUpdateCoordinator], RestoreEntity, SwitchEntity
):
    """Switch entity for HAEO input configuration.

    Created from subentry configuration during platform setup.
    Extends CoordinatorEntity to receive coordinator updates.

    Supports two modes:
    - Editable: User controls the value, persisted with RestoreEntity
    - Driven: Value and forecast come from coordinator's loaded config (extractor output)
    """

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: HaeoDataUpdateCoordinator,
        config_entry: ConfigEntry,
        subentry: ConfigSubentry,
        field_info: InputFieldInfo,
        device_entry: DeviceEntry,
    ) -> None:
        """Initialize the input switch entity.

        Args:
            hass: Home Assistant instance
            coordinator: Data update coordinator for this entry
            config_entry: Parent config entry
            subentry: Element subentry containing configuration
            field_info: Metadata about this input field
            device_entry: Device registry entry for this entity's device

        """
        super().__init__(coordinator)

        self.hass = hass
        self._config_entry = config_entry
        self._subentry = subentry
        self._field_info = field_info
        self._field_name = field_info.field_name
        self._output_type = field_info.output_type
        self._element_type = subentry.subentry_type
        self._element_name = subentry.title

        # Determine mode from config value - can be entity ID(s) or static value
        config_value = subentry.data.get(self._field_name)
        self._source_entity_ids: list[str] = []

        if isinstance(config_value, str) and "." in config_value:
            # Single entity ID - Driven mode
            self._entity_mode = ConfigEntityMode.DRIVEN
            self._source_entity_ids = [config_value]
            self._attr_is_on = False
        elif isinstance(config_value, list) and config_value and all(isinstance(item, str) for item in config_value):
            # Multiple entity IDs - Driven mode
            self._entity_mode = ConfigEntityMode.DRIVEN
            self._source_entity_ids = config_value
            self._attr_is_on = False
        else:
            # Static value or missing - Editable mode
            self._entity_mode = ConfigEntityMode.EDITABLE
            if isinstance(config_value, bool):
                self._attr_is_on = config_value
            else:
                # Will be set properly in async_added_to_hass using data_default
                self._attr_is_on = bool(config_value) if config_value is not None else None

        # Store data default for use when no value is available
        self._data_default = field_info.data_default

        # Entity attributes
        self._attr_unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_{field_info.field_name}"
        self._attr_translation_key = field_info.translation_key
        self._attr_translation_placeholders = {k: str(v) for k, v in subentry.data.items()}

        # Device info - use identifiers from device_entry to ensure proper subentry association
        self._attr_device_info = DeviceInfo(
            identifiers=device_entry.identifiers,
        )

        # Note: device_class not used for switches since InputFieldInfo is number-focused

        # Set extra state attributes
        self._update_extra_attributes()

    def _update_extra_attributes(self, *, forecast: list[dict[str, Any]] | None = None) -> None:
        """Update extra state attributes.

        Args:
            forecast: Forecast data to include in attributes (from coordinator's loaded config)

        """
        attrs: dict[str, Any] = {
            "element_name": self._element_name,
            "element_type": self._element_type,
            "output_name": self._field_name,
            "output_type": self._output_type,
            "config_mode": self._entity_mode.value,
        }
        if self._source_entity_ids:
            attrs["source_entities"] = self._source_entity_ids
        if forecast is not None:
            attrs["forecast"] = forecast
        self._attr_extra_state_attributes = attrs

    async def async_added_to_hass(self) -> None:
        """Handle entity being added to Home Assistant."""
        await super().async_added_to_hass()

        if self._entity_mode == ConfigEntityMode.EDITABLE:
            # Restore previous value if available
            last_state = await self.async_get_last_state()
            if last_state is not None:
                self._attr_is_on = last_state.state == "on"
            elif self._attr_is_on is None:
                # Use data default when no restored value and no config value
                if self._data_default is not None:
                    self._attr_is_on = bool(self._data_default)
                else:
                    self._attr_is_on = False

        # Get initial forecast from coordinator if available
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle coordinator update to get forecast from loaded configs.

        The forecast comes from the extractor output (loaded config values),
        not from the source entity directly. This ensures the forecast reflects
        what the optimizer actually uses.

        In driven mode, the state is also updated from the first loaded value.
        In editable mode, the state remains user-controlled.
        """
        # Get element data containing inputs (loaded config) and outputs
        element_data = self.coordinator.data["elements"].get(self._element_name)
        if element_data is None:
            return

        # Get loaded values for this field from inputs
        loaded_config = element_data["inputs"]
        field_values = loaded_config.get(self._field_name)
        if field_values is None:
            return

        # Build forecast from loaded values and timestamps
        forecast = self._build_forecast_from_loaded_values(field_values, self.coordinator.data["forecast_timestamps"])

        # In driven mode, update state from first loaded value
        if self._entity_mode == ConfigEntityMode.DRIVEN:
            if isinstance(field_values, list | tuple) and len(field_values) > 0:
                self._attr_is_on = bool(field_values[0])
            elif isinstance(field_values, bool):
                self._attr_is_on = field_values

        self._update_extra_attributes(forecast=forecast)
        self.async_write_ha_state()

    def _build_forecast_from_loaded_values(
        self,
        values: Any,
        forecast_timestamps: tuple[float, ...] | None,
    ) -> list[dict[str, Any]] | None:
        """Build forecast attribute from loaded config values.

        Args:
            values: Loaded values from config (list/tuple for time series, scalar for constants)
            forecast_timestamps: Timestamps for each period from coordinator

        Returns:
            List of forecast points with time and value, or None if not applicable

        """
        if forecast_timestamps is None:
            return None

        # Handle scalar values (constant across all periods)
        if isinstance(values, bool):
            values = [values] * len(forecast_timestamps)
        elif not isinstance(values, list | tuple):
            return None

        if len(values) == 0:
            return None

        # Only create forecast if we have multiple values
        if len(values) <= 1:
            return None

        local_tz = dt_util.get_default_time_zone()
        return [
            {
                "time": datetime.fromtimestamp(timestamp, tz=local_tz).isoformat(),
                "value": value,
            }
            for timestamp, value in zip(forecast_timestamps, values, strict=False)
        ]

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Turn the switch on.

        In Editable mode: stores the value and triggers coordinator refresh.
        In Driven mode: ignored - value is controlled by coordinator.
        """
        if self._entity_mode == ConfigEntityMode.DRIVEN:
            _LOGGER.debug("Ignoring turn_on in Driven mode for %s", self.entity_id)
            return

        self._attr_is_on = True
        self.async_write_ha_state()

        # Trigger coordinator refresh
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Turn the switch off.

        In Editable mode: stores the value and triggers coordinator refresh.
        In Driven mode: ignored - value is controlled by coordinator.
        """
        if self._entity_mode == ConfigEntityMode.DRIVEN:
            _LOGGER.debug("Ignoring turn_off in Driven mode for %s", self.entity_id)
            return

        self._attr_is_on = False
        self.async_write_ha_state()

        # Trigger coordinator refresh
        await self.coordinator.async_request_refresh()

    def get_current_value(self) -> bool:
        """Return the current value for use by the optimizer.

        This is called by the coordinator when loading input values.
        """
        return bool(self._attr_is_on)


__all__ = ["HaeoInputSwitch"]
