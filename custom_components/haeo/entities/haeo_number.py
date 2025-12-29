"""Number entity for HAEO input configuration."""

from collections.abc import Callable
from enum import Enum
from typing import Any

from homeassistant.components.number import RestoreNumber
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.event import EventStateChangedData, async_track_state_change_event

from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.schema.input_fields import InputFieldInfo
from custom_components.haeo.util.forecast_times import generate_forecast_timestamps, tiers_to_periods_seconds


class ConfigEntityMode(Enum):
    """Operating mode for config entities."""

    EDITABLE = "editable"  # User can set value, no external source
    DRIVEN = "driven"  # Value driven by external entity


def _is_entity_id(value: Any) -> bool:
    """Check if a value looks like an entity ID.

    Entity IDs contain a domain separator (e.g., sensor.temperature).
    Element names and other strings don't have dots.
    """
    return isinstance(value, str) and "." in value


def _extract_source_entity_ids(config_value: Any) -> list[str]:
    """Extract entity IDs from a config value.

    Handles both single entity IDs and lists of entity IDs.
    """
    if isinstance(config_value, list):
        return [v for v in config_value if _is_entity_id(v)]
    if _is_entity_id(config_value):
        return [config_value]
    return []


class HaeoInputNumber(RestoreNumber):
    """Number entity representing a configurable input parameter.

    This entity serves as an intermediate layer between external sensors
    and the optimization model. It can operate in two modes:

    - EDITABLE: User can directly set the value. Used when config contains
      a static value rather than an entity ID.
    - DRIVEN: Value is driven by an external sensor. Used when config
      contains an entity ID. In this mode, user edits are ignored.

    Both modes provide a forecast attribute with values across the time horizon.
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
        device_entry: DeviceEntry,
    ) -> None:
        """Initialize the input number entity.

        Args:
            hass: Home Assistant instance
            config_entry: Parent config entry (the hub)
            subentry: Config subentry for this element
            field_info: Metadata about this input field
            device_entry: Device entry to associate this entity with

        """
        self._hass = hass
        self._config_entry = config_entry
        self._subentry = subentry
        self._field_info = field_info

        # Set device_id directly to link entity to device without device_info
        self._attr_device_id = device_entry.id

        # Determine mode from config value
        config_value = subentry.data.get(field_info.field_name)
        source_entity_ids = _extract_source_entity_ids(config_value)

        if source_entity_ids:
            self._entity_mode = ConfigEntityMode.DRIVEN
            self._source_entity_ids = source_entity_ids
            self._attr_native_value = None  # Will be set when data loads
        else:
            self._entity_mode = ConfigEntityMode.EDITABLE
            self._source_entity_ids = []
            # Set initial value from config (may be None for optional fields)
            if config_value is not None:
                self._attr_native_value = float(config_value)
            else:
                self._attr_native_value = None

        # Unique ID for multi-hub safety: entry_id + subentry_id + field_name
        self._attr_unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_{field_info.field_name}"

        # Entity attributes from field info
        self._attr_translation_key = field_info.translation_key or field_info.field_name
        self._attr_native_unit_of_measurement = field_info.unit
        self._attr_device_class = field_info.device_class
        if field_info.min_value is not None:
            self._attr_native_min_value = field_info.min_value
        if field_info.max_value is not None:
            self._attr_native_max_value = field_info.max_value
        if field_info.step is not None:
            self._attr_native_step = field_info.step

        # Pass subentry data as translation placeholders
        self._attr_translation_placeholders = {k: str(v) for k, v in subentry.data.items()}

        # Build base extra state attributes (static values)
        self._base_extra_attrs: dict[str, Any] = {
            "config_mode": self._entity_mode.value,
            "element_name": subentry.title,
            "element_type": subentry.subentry_type,
            "field_name": field_info.field_name,
            "output_type": field_info.output_type,
            "time_series": field_info.time_series,
        }
        if self._source_entity_ids:
            self._base_extra_attrs["source_entities"] = self._source_entity_ids
        if field_info.direction:
            self._base_extra_attrs["direction"] = field_info.direction
        self._attr_extra_state_attributes = dict(self._base_extra_attrs)

        # Loader for time series data
        self._loader = TimeSeriesLoader()
        self._state_unsub: Callable[[], None] | None = None

    def _get_forecast_timestamps(self) -> tuple[float, ...]:
        """Get forecast timestamps from hub config for consistent time horizon."""
        periods_seconds = tiers_to_periods_seconds(self._config_entry.data)
        return generate_forecast_timestamps(periods_seconds)

    async def async_added_to_hass(self) -> None:
        """Set up state tracking and restore previous value."""
        await super().async_added_to_hass()

        if self._entity_mode == ConfigEntityMode.EDITABLE:
            # Restore previous value if available
            last_data = await self.async_get_last_number_data()
            if last_data and last_data.native_value is not None:
                self._attr_native_value = last_data.native_value
            # Update forecast for restored/initial value
            self._update_editable_forecast()
        else:
            # Subscribe to source entity changes for DRIVEN mode
            self._state_unsub = async_track_state_change_event(
                self._hass,
                self._source_entity_ids,
                self._handle_source_state_change,
            )
            # Load initial data
            self._hass.async_create_task(self._async_load_data())

    async def async_will_remove_from_hass(self) -> None:
        """Clean up state tracking."""
        if self._state_unsub is not None:
            self._state_unsub()
            self._state_unsub = None
        await super().async_will_remove_from_hass()

    @callback
    def _handle_source_state_change(self, _event: Event[EventStateChangedData]) -> None:
        """Handle source entity state change."""
        self._hass.async_create_task(self._async_load_data())

    async def _async_load_data(self) -> None:
        """Load data from source entities and update state."""
        forecast_timestamps = self._get_forecast_timestamps()

        try:
            values = await self._loader.load(
                hass=self._hass,
                value=self._source_entity_ids,
                forecast_times=list(forecast_timestamps),
            )
        except Exception:
            # If loading fails, don't update state
            return

        if not values:
            return

        # Build updated extra state attributes
        extra_attrs = dict(self._base_extra_attrs)
        extra_attrs["forecast"] = values
        extra_attrs["forecast_timestamps"] = list(forecast_timestamps)

        # Update native value to current (first) value
        self._attr_native_value = values[0]
        self._attr_extra_state_attributes = extra_attrs
        self.async_write_ha_state()

    def _update_editable_forecast(self) -> None:
        """Update forecast attribute for editable mode with constant value."""
        forecast_timestamps = self._get_forecast_timestamps()

        extra_attrs = dict(self._base_extra_attrs)
        extra_attrs["forecast_timestamps"] = list(forecast_timestamps)

        if self._attr_native_value is not None:
            # Constant value across entire horizon
            extra_attrs["forecast"] = [self._attr_native_value] * len(forecast_timestamps)

        self._attr_extra_state_attributes = extra_attrs

    async def async_set_native_value(self, value: float) -> None:
        """Handle user setting a value.

        In DRIVEN mode, user changes are effectively ignored because the
        source entity will overwrite with its value.
        """
        if self._entity_mode == ConfigEntityMode.DRIVEN:
            # Read-only in driven mode, but we still update to avoid confusion
            self.async_write_ha_state()
            return

        self._attr_native_value = value
        self._update_editable_forecast()
        self.async_write_ha_state()


__all__ = ["ConfigEntityMode", "HaeoInputNumber"]
