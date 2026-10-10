"""Horizon manager for HAEO forecast time windows.

This module provides the HorizonManager class which manages the forecast time horizon
used by all input entities. It is a pure Python class (not an entity) that can be
created early in the setup process before any platforms are loaded.

The HorizonManager:
- Computes forecast timestamps from a horizon preset, aligned to period boundaries,
  or reads them from a HAEO-format forecast entity
- Updates a preset horizon at each period boundary, and an entity horizon whenever
  the entity changes
- Provides callbacks for dependent components to subscribe to horizon changes
"""

from collections.abc import Callable
from datetime import datetime
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import async_track_point_in_time, async_track_state_change_event
from homeassistant.util import dt as dt_util

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import CONF_HORIZON, HUB_SECTION_COMMON
from custom_components.haeo.core.data.forecast_times import (
    floor_timestamp,
    forecast_boundaries,
    generate_forecast_timestamps,
    periods_seconds_from_boundaries,
    preset_periods_seconds,
)
from custom_components.haeo.core.schema.horizon_value import HorizonValue, is_horizon_preset_value

_LOGGER = logging.getLogger(__name__)


class HorizonManager:
    """Manager for the forecast time horizon.

    This class:
    - Provides forecast timestamps for all input entities to use
    - Updates a preset horizon at period boundaries, and an entity horizon when
      the entity changes
    - Notifies subscribers when the horizon changes

    Unlike HaeoHorizonEntity, this is a pure Python object that can be
    created before any entity platforms are set up.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the horizon manager.

        Raises:
            ConfigEntryNotReady: If the horizon entity does not yet provide a usable forecast.

        """
        self._hass = hass
        self._horizon: HorizonValue = config_entry.data[HUB_SECTION_COMMON][CONF_HORIZON]

        self._periods_seconds: list[int] = []
        self._smallest_period = 60

        # Timer for the next preset update, or listener for horizon entity changes
        self._unsub_update: CALLBACK_TYPE | None = None

        # Subscribers to horizon changes
        self._subscribers: list[Callable[[], None]] = []

        # Current forecast timestamps (cached)
        self._forecast_timestamps: tuple[float, ...] = ()

        self._update_timestamps()
        if not self._forecast_timestamps:
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="horizon_entity_not_ready",
                translation_placeholders={"entity_id": self._horizon["value"][0]},
            )

    def _update_timestamps(self) -> bool:
        """Update the cached forecast timestamps, returning whether they changed.

        An entity horizon whose forecast cannot be read keeps the previous horizon.
        """
        if is_horizon_preset_value(self._horizon):
            now = dt_util.now()
            preset = self._horizon["value"]
            self._smallest_period = min(preset_periods_seconds(preset, start_time=now))
            start_ts = floor_timestamp(now.timestamp(), self._smallest_period)
            start_dt = datetime.fromtimestamp(start_ts, tz=now.tzinfo)
            self._periods_seconds = preset_periods_seconds(preset, start_time=start_dt)
            previous = self._forecast_timestamps
            self._forecast_timestamps = generate_forecast_timestamps(self._periods_seconds, start_ts)
            return self._forecast_timestamps != previous

        entity_id = self._horizon["value"][0]
        state = self._hass.states.get(entity_id)
        if state is None:
            _LOGGER.warning("Keeping the current horizon because %s is not available", entity_id)
            return False
        try:
            boundaries = forecast_boundaries(state)
        except ValueError as err:
            _LOGGER.warning("Keeping the current horizon: %s", err)
            return False
        if boundaries == self._forecast_timestamps:
            return False
        self._forecast_timestamps = boundaries
        self._periods_seconds = periods_seconds_from_boundaries(boundaries)
        self._smallest_period = min(self._periods_seconds)
        return True

    def start(self) -> Callable[[], None]:
        """Start the scheduled updates.

        Call this after the manager is fully initialized and ready to
        receive timer callbacks.

        Returns:
            A stop function that can be passed to async_on_unload.

        """
        self._schedule_next_update()
        return self.stop

    def stop(self) -> None:
        """Stop scheduled updates and clean up resources."""
        if self._unsub_update is not None:
            self._unsub_update()
            self._unsub_update = None
        # Clear all subscribers to prevent stale callbacks during reload
        self._subscribers.clear()

    def pause(self) -> None:
        """Pause scheduled updates without clearing subscribers.

        Used when auto-optimize is disabled to freeze the horizon in time.
        Call resume() to restart updates.
        """
        if self._unsub_update is not None:
            self._unsub_update()
            self._unsub_update = None

    def resume(self) -> None:
        """Resume scheduled updates after being paused.

        Updates timestamps to current time, notifies all subscribers,
        and restarts the update timer.
        """
        self._update_timestamps()

        # Notify all subscribers of the resumed horizon
        for subscriber in self._subscribers:
            subscriber()

        # Restart the timer
        self._schedule_next_update()

    def _schedule_next_update(self) -> None:
        """Schedule the next horizon update.

        A preset horizon updates at the next period boundary, and an entity
        horizon whenever the entity changes. Any update already scheduled is
        cancelled first, so resuming never leaves two running.
        """
        self.pause()
        if not is_horizon_preset_value(self._horizon):
            self._unsub_update = async_track_state_change_event(
                self._hass, self._horizon["value"][0], self._async_entity_update
            )
            return

        now = dt_util.utcnow()
        epoch_seconds = now.timestamp()

        # Calculate next period boundary
        current_boundary = floor_timestamp(epoch_seconds, self._smallest_period)
        next_boundary = current_boundary + self._smallest_period

        # Convert to datetime for scheduling
        next_update_time = datetime.fromtimestamp(next_boundary, tz=dt_util.UTC)

        self._unsub_update = async_track_point_in_time(
            self._hass,
            self._async_scheduled_update,
            next_update_time,
        )

    @callback
    def _async_scheduled_update(self, _now: datetime) -> None:
        """Handle scheduled update when period boundary is reached."""
        self._update_timestamps()

        # Notify all subscribers
        for subscriber in self._subscribers:
            subscriber()

        # Schedule next update
        self._schedule_next_update()

    @callback
    def _async_entity_update(self, _event: Event[EventStateChangedData]) -> None:
        """Handle a change to the horizon entity, notifying subscribers if its boundaries changed."""
        if self._update_timestamps():
            for subscriber in self._subscribers:
                subscriber()

    def subscribe(self, callback_fn: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to horizon changes.

        Args:
            callback_fn: Function to call when horizon changes

        Returns:
            Unsubscribe function to remove the subscription

        """
        self._subscribers.append(callback_fn)

        def unsubscribe() -> None:
            if callback_fn in self._subscribers:
                self._subscribers.remove(callback_fn)

        return unsubscribe

    def get_forecast_timestamps(self) -> tuple[float, ...]:
        """Get the current forecast timestamps as epoch values.

        Returns boundary timestamps for the horizon (n_periods + 1 values).
        """
        return self._forecast_timestamps

    @property
    def periods_seconds(self) -> list[int]:
        """Get the period durations in seconds."""
        return self._periods_seconds

    @property
    def smallest_period(self) -> int:
        """Get the smallest period duration in seconds."""
        return self._smallest_period

    @property
    def period_count(self) -> int:
        """Get the number of periods in the horizon."""
        return len(self._periods_seconds)

    @property
    def current_start_time(self) -> datetime | None:
        """Get the current period start time as a datetime."""
        if self._forecast_timestamps:
            local_tz = dt_util.get_default_time_zone()
            return datetime.fromtimestamp(self._forecast_timestamps[0], tz=local_tz)
        return None


__all__ = ["HorizonManager"]
