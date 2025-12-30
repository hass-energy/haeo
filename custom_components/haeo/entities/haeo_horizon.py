"""Horizon entity for HAEO forecast time windows.

This entity provides the common forecast time horizon used by all input entities.
It updates on a schedule based on the smallest tier duration, and its state changes
trigger dependent entities to refresh their forecasts via standard HA state tracking.
"""

from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util import dt as dt_util

from custom_components.haeo.util.forecast_times import generate_forecast_timestamps, tiers_to_periods_seconds


class HaeoHorizonEntity(SensorEntity):
    """Entity representing the forecast time horizon.

    This entity:
    - Provides forecast timestamps for all input entities to use
    - Updates on a schedule aligned to the smallest period boundary
    - State changes trigger dependent entities via HA state tracking

    The entity state shows the current period start time, and the forecast
    attribute contains all fence-post timestamps for the horizon.
    """

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "horizon"

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        device_entry: DeviceEntry,
    ) -> None:
        """Initialize the horizon entity."""
        self._hass = hass
        self._config_entry = config_entry

        # Set device_entry to link entity to device
        self.device_entry = device_entry

        # Unique ID for multi-hub safety
        self._attr_unique_id = f"{config_entry.entry_id}_horizon"

        # Calculate period durations from config
        self._periods_seconds = tiers_to_periods_seconds(config_entry.data)
        self._smallest_period = min(self._periods_seconds)

        # Timer for next update
        self._unsub_timer: CALLBACK_TYPE | None = None

        # Initialize state
        self._update_horizon()

    def _update_horizon(self) -> None:
        """Update the horizon timestamps and state."""
        forecast_timestamps = generate_forecast_timestamps(self._periods_seconds)

        # Build forecast as list of ForecastPoint-style dicts
        local_tz = dt_util.get_default_time_zone()
        forecast = [{"time": datetime.fromtimestamp(ts, tz=local_tz), "value": None} for ts in forecast_timestamps]

        # State is the current period start time
        if forecast_timestamps:
            self._attr_native_value = datetime.fromtimestamp(forecast_timestamps[0], tz=local_tz).isoformat()
        else:
            self._attr_native_value = None

        self._attr_extra_state_attributes = {
            "forecast": forecast,
            "period_count": len(self._periods_seconds),
            "smallest_period_seconds": self._smallest_period,
        }

    def _schedule_next_update(self) -> None:
        """Schedule the next horizon update at the next period boundary."""
        now = dt_util.utcnow()
        epoch_seconds = now.timestamp()

        # Calculate next period boundary
        current_boundary = epoch_seconds // self._smallest_period * self._smallest_period
        next_boundary = current_boundary + self._smallest_period

        # Convert to datetime for scheduling
        next_update_time = datetime.fromtimestamp(next_boundary, tz=dt_util.UTC)

        self._unsub_timer = async_track_point_in_time(
            self._hass,
            self._async_scheduled_update,
            next_update_time,
        )

    @callback
    def _async_scheduled_update(self, _now: datetime) -> None:
        """Handle scheduled update when period boundary is reached."""
        self._update_horizon()
        self.async_write_ha_state()

        # Schedule next update
        self._schedule_next_update()

    async def async_added_to_hass(self) -> None:
        """Set up the scheduled updates when entity is added."""
        await super().async_added_to_hass()
        self._schedule_next_update()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up timer when entity is removed."""
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None
        await super().async_will_remove_from_hass()

    def get_forecast_timestamps(self) -> tuple[float, ...]:
        """Get the current forecast timestamps as epoch values."""
        return generate_forecast_timestamps(self._periods_seconds)


__all__ = ["HaeoHorizonEntity"]
