"""Horizon entity for HAEO forecast time windows.

This entity displays the current horizon state from the HorizonManager.
It is a read-only sensor that provides visibility into the forecast time window.
"""

from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.util import dt as dt_util

from custom_components.haeo.const import OUTPUT_NAME_HORIZON
from custom_components.haeo.horizon import HorizonManager


class HaeoHorizonEntity(SensorEntity):
    """Entity displaying the forecast time horizon.

    This entity:
    - Reads state from the HorizonManager
    - Updates when the HorizonManager notifies of changes
    - Provides user visibility into the current forecast window

    The entity state shows the current period start time, and the forecast
    attribute contains all boundary timestamps for the horizon.
    """

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "horizon"

    def __init__(
        self,
        config_entry: ConfigEntry,
        device_entry: DeviceEntry,
        horizon_manager: HorizonManager,
    ) -> None:
        """Initialize the horizon entity."""
        self._config_entry = config_entry
        self._horizon_manager = horizon_manager

        # Set device_entry to link entity to device
        self.device_entry = device_entry

        # Unique ID for multi-hub safety
        self._attr_unique_id = f"{config_entry.entry_id}_{OUTPUT_NAME_HORIZON}"

        # Initialize state from manager
        self._update_state()

    def _update_state(self) -> None:
        """Update state from the horizon manager."""
        forecast_timestamps = self._horizon_manager.get_forecast_timestamps()

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
            "period_count": self._horizon_manager.period_count,
            "smallest_period_seconds": self._horizon_manager.smallest_period,
        }

    @callback
    def _async_horizon_changed(self) -> None:
        """Handle horizon manager state change."""
        self._update_state()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Subscribe to horizon manager when entity is added."""
        await super().async_added_to_hass()
        self.async_on_remove(self._horizon_manager.subscribe(self._async_horizon_changed))


__all__ = ["HaeoHorizonEntity"]
