"""Input switch entity for HAEO runtime configuration."""

from datetime import datetime
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.schema.input_fields import InputFieldInfo

from .mode import ConfigEntityMode

if TYPE_CHECKING:
    from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class HaeoInputSwitch(RestoreEntity, SwitchEntity):
    """Switch entity for HAEO input configuration.

    Created directly from subentry configuration during platform setup.
    Does not require coordinator to exist.

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
        config_entry: ConfigEntry,
        subentry: ConfigSubentry,
        field_info: InputFieldInfo,
        device_id: str,
    ) -> None:
        """Initialize the input switch entity.

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
        self._output_type = field_info.output_type
        self._element_type = subentry.subentry_type
        self._element_name = subentry.title

        # Determine mode from config value
        config_value = subentry.data.get(self._field_name)
        self._source_entity_id: str | None = None

        if isinstance(config_value, str) and "." in config_value:
            # Looks like an entity ID - Driven mode
            self._entity_mode = ConfigEntityMode.DRIVEN
            self._source_entity_id = config_value
            self._attr_is_on = False
        else:
            # Static value or missing - Editable mode
            self._entity_mode = ConfigEntityMode.EDITABLE
            if isinstance(config_value, bool):
                self._attr_is_on = config_value
            else:
                self._attr_is_on = (
                    bool(config_value) if config_value is not None else False
                )

        # Entity attributes
        self._attr_unique_id = (
            f"{config_entry.entry_id}_{subentry.subentry_id}_{field_info.field_name}"
        )
        self._attr_translation_key = field_info.translation_key
        self._attr_translation_placeholders = {
            k: str(v) for k, v in subentry.data.items()
        }

        # Device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{config_entry.entry_id}_{device_id}")},
        )

        # Note: device_class not used for switches since InputFieldInfo is number-focused

        # Unsubscribe callbacks for state change and coordinator listeners
        self._unsub_state_change: Any = None
        self._unsub_coordinator: Any = None

        # Set extra state attributes
        self._update_extra_attributes()

    @property
    def entity_mode(self) -> ConfigEntityMode:
        """Return the current entity mode."""
        return self._entity_mode

    def _update_extra_attributes(
        self, *, forecast: list[dict[str, Any]] | None = None
    ) -> None:
        """Update extra state attributes.

        Args:
            forecast: Forecast data to include in attributes (from coordinator's loaded config)

        """
        attrs: dict[str, Any] = {
            "element_name": self._element_name,
            "element_type": self._element_type,
            "output_name": self._field_name,
            "output_type": self._output_type,
            "entity_mode": self._entity_mode.value,
        }
        if self._source_entity_id:
            attrs["source_entity"] = self._source_entity_id
        if forecast is not None:
            attrs["forecast"] = forecast
        self._attr_extra_state_attributes = attrs

    def _get_coordinator(self) -> "HaeoDataUpdateCoordinator | None":
        """Get the coordinator from the config entry."""
        return getattr(self._config_entry, "runtime_data", None)

    async def async_added_to_hass(self) -> None:
        """Handle entity being added to Home Assistant."""
        await super().async_added_to_hass()

        if self._entity_mode == ConfigEntityMode.EDITABLE:
            # Restore previous value if available
            last_state = await self.async_get_last_state()
            if last_state is not None:
                self._attr_is_on = last_state.state == "on"

        # Subscribe to coordinator updates to get forecast from loaded configs
        coordinator = self._get_coordinator()
        if coordinator is not None:
            self._unsub_coordinator = coordinator.async_add_listener(
                self._handle_coordinator_update
            )
            # Get initial forecast from coordinator if available
            self._handle_coordinator_update()

    async def async_will_remove_from_hass(self) -> None:
        """Handle entity being removed from Home Assistant."""
        await super().async_will_remove_from_hass()

        if self._unsub_state_change:
            self._unsub_state_change()
            self._unsub_state_change = None

        if self._unsub_coordinator:
            self._unsub_coordinator()
            self._unsub_coordinator = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle coordinator update to get forecast from loaded configs.

        The forecast comes from the extractor output (loaded config values),
        not from the source entity directly. This ensures the forecast reflects
        what the optimizer actually uses.

        In driven mode, the state is also updated from the first loaded value.
        In editable mode, the state remains user-controlled.
        """
        coordinator = self._get_coordinator()
        if coordinator is None or coordinator.loaded_configs is None:
            return

        # Get loaded values for this field from coordinator
        loaded_config = coordinator.loaded_configs.get(self._element_name)
        if loaded_config is None:
            return

        field_values = loaded_config.get(self._field_name)
        if field_values is None:
            return

        # Build forecast from loaded values and timestamps
        forecast = self._build_forecast_from_loaded_values(
            field_values, coordinator.forecast_timestamps
        )

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

        # Trigger coordinator refresh if available
        coordinator = self._get_coordinator()
        if coordinator is not None:
            await coordinator.async_request_refresh()

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

        # Trigger coordinator refresh if available
        coordinator = self._get_coordinator()
        if coordinator is not None:
            await coordinator.async_request_refresh()

    def get_current_value(self) -> bool:
        """Return the current value for use by the optimizer.

        This is called by the coordinator when loading input values.
        """
        return bool(self._attr_is_on)


__all__ = ["HaeoInputSwitch"]
