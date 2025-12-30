"""Number entity for HAEO input configuration."""

from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from homeassistant.components.number import NumberEntityDescription, RestoreNumber
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.event import EventStateChangedData, async_track_state_change_event
from homeassistant.util import dt as dt_util

from custom_components.haeo import HaeoConfigEntry
from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.elements.input_fields import InputFieldInfo

if TYPE_CHECKING:
    from custom_components.haeo.entities.haeo_horizon import HaeoHorizonEntity


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
        config_entry: HaeoConfigEntry,
        subentry: ConfigSubentry,
        field_info: InputFieldInfo[NumberEntityDescription],
        device_entry: DeviceEntry,
        horizon_entity: "HaeoHorizonEntity",
    ) -> None:
        """Initialize the input number entity.

        Args:
            hass: Home Assistant instance
            config_entry: Parent config entry (the hub)
            subentry: Config subentry for this element
            field_info: Metadata about this input field
            device_entry: Device entry to associate this entity with
            horizon_entity: Horizon entity providing forecast timestamps

        """
        self._hass = hass
        self._config_entry: HaeoConfigEntry = config_entry
        self._subentry = subentry
        self._field_info = field_info
        self._horizon_entity = horizon_entity

        # Set device_entry to link entity to device
        self.device_entry = device_entry

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
            self._attr_native_value = float(config_value) if config_value is not None else None

        # Unique ID for multi-hub safety: entry_id + subentry_id + field_name
        self._attr_unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_{field_info.field_name}"

        # Use entity description directly from field info
        self.entity_description = field_info.entity_description

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
        self._horizon_unsub: Callable[[], None] | None = None

    def _get_forecast_timestamps(self) -> tuple[float, ...]:
        """Get forecast timestamps from horizon entity."""
        return self._horizon_entity.get_forecast_timestamps()

    async def async_added_to_hass(self) -> None:
        """Set up state tracking and restore previous value."""
        await super().async_added_to_hass()

        # Subscribe to horizon updates for consistent time windows
        self._horizon_unsub = self._horizon_entity.async_subscribe(self._handle_horizon_update)

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
        if self._horizon_unsub is not None:
            self._horizon_unsub()
            self._horizon_unsub = None
        await super().async_will_remove_from_hass()

    @callback
    def _handle_horizon_update(self) -> None:
        """Handle horizon update - refresh forecast with new time windows."""
        if self._entity_mode == ConfigEntityMode.EDITABLE:
            self._update_editable_forecast()
            self.async_write_ha_state()
        else:
            # Re-load data for driven mode
            self._hass.async_create_task(self._async_load_data())

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

        # Build forecast as list of ForecastPoint-style dicts
        local_tz = dt_util.get_default_time_zone()
        forecast = [
            {"time": datetime.fromtimestamp(ts, tz=local_tz), "value": val}
            for ts, val in zip(forecast_timestamps, values, strict=False)
        ]

        # Build updated extra state attributes
        extra_attrs = dict(self._base_extra_attrs)
        extra_attrs["forecast"] = forecast

        # Update native value to current (first) value
        self._attr_native_value = values[0]
        self._attr_extra_state_attributes = extra_attrs
        self.async_write_ha_state()

    def _update_editable_forecast(self) -> None:
        """Update forecast attribute for editable mode with constant value."""
        forecast_timestamps = self._get_forecast_timestamps()

        extra_attrs = dict(self._base_extra_attrs)

        if self._attr_native_value is not None:
            # Build forecast as list of ForecastPoint-style dicts with constant value
            local_tz = dt_util.get_default_time_zone()
            forecast = [
                {"time": datetime.fromtimestamp(ts, tz=local_tz), "value": self._attr_native_value}
                for ts in forecast_timestamps
            ]
            extra_attrs["forecast"] = forecast

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
