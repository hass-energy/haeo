"""Horizon manager for HAEO forecast time windows.

This module provides the HorizonManager class which manages the forecast time horizon
used by all input entities. It is a pure Python class (not an entity) that can be
created early in the setup process before any platforms are loaded.

The HorizonManager:
- Computes forecast timestamps based on tier configuration with dynamic alignment
- Schedules updates at period boundaries
- Provides callbacks for dependent components to subscribe to horizon changes
"""

from collections.abc import Callable
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util import dt as dt_util

from custom_components.haeo.const import (
    CONF_HORIZON_DURATION_MINUTES,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_DURATION,
    DEFAULT_HORIZON_DURATION_MINUTES,
    DEFAULT_TIER_1_COUNT,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_2_COUNT,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_COUNT,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_DURATION,
)
from custom_components.haeo.util.forecast_times import (
    calculate_aligned_tier_counts,
    calculate_worst_case_total_steps,
    generate_forecast_timestamps,
)


class HorizonManager:
    """Manager for the forecast time horizon.

    This class:
    - Provides forecast timestamps for all input entities to use
    - Schedules updates at period boundaries with dynamic tier alignment
    - Notifies subscribers when the horizon changes

    Unlike HaeoHorizonEntity, this is a pure Python object that can be
    created before any entity platforms are set up.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the horizon manager."""
        self._hass = hass
        self._config_entry = config_entry

        # Extract tier configuration from config
        config = config_entry.data
        self._tier_durations: tuple[int, int, int, int] = (
            config.get(CONF_TIER_1_DURATION, DEFAULT_TIER_1_DURATION),
            config.get(CONF_TIER_2_DURATION, DEFAULT_TIER_2_DURATION),
            config.get(CONF_TIER_3_DURATION, DEFAULT_TIER_3_DURATION),
            config.get(CONF_TIER_4_DURATION, DEFAULT_TIER_4_DURATION),
        )
        self._min_counts: tuple[int, int, int] = (
            config.get(CONF_TIER_1_COUNT, DEFAULT_TIER_1_COUNT),
            config.get(CONF_TIER_2_COUNT, DEFAULT_TIER_2_COUNT),
            config.get(CONF_TIER_3_COUNT, DEFAULT_TIER_3_COUNT),
        )
        self._horizon_minutes: int = config.get(CONF_HORIZON_DURATION_MINUTES, DEFAULT_HORIZON_DURATION_MINUTES)

        # Calculate total steps based on worst-case alignment (consistent solver size)
        self._total_steps = calculate_worst_case_total_steps(
            self._min_counts, self._tier_durations, self._horizon_minutes
        )

        # Smallest period for scheduling (T1 duration in seconds)
        self._smallest_period = self._tier_durations[0] * 60

        # Timer for next update
        self._unsub_timer: CALLBACK_TYPE | None = None

        # Subscribers to horizon changes
        self._subscribers: list[Callable[[], None]] = []

        # Current periods and forecast timestamps (updated dynamically)
        self._periods_seconds: list[int] = []
        self._forecast_timestamps: tuple[float, ...] = ()

        # Initialize timestamps with aligned periods
        self._update_timestamps()

    def _update_timestamps(self) -> None:
        """Update cached timestamps with aligned tier counts."""
        now = dt_util.utcnow()

        # Calculate aligned periods based on current time
        self._periods_seconds, _ = calculate_aligned_tier_counts(
            start_time=now,
            tier_durations=self._tier_durations,
            min_counts=self._min_counts,
            total_steps=self._total_steps,
            horizon_minutes=self._horizon_minutes,
        )

        self._forecast_timestamps = generate_forecast_timestamps(self._periods_seconds)

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
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None
        # Clear all subscribers to prevent stale callbacks during reload
        self._subscribers.clear()

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
        self._update_timestamps()

        # Notify all subscribers
        for subscriber in self._subscribers:
            subscriber()

        # Schedule next update
        self._schedule_next_update()

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
