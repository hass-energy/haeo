"""Horizon manager for HAEO forecast time windows.

This module provides the HorizonManager class which manages the forecast time horizon
used by all input entities. It is a pure Python class (not an entity) that can be
created early in the setup process before any platforms are loaded.

The HorizonManager:
- Computes forecast timestamps from tier presets or an external HAEO-format entity
- Schedules updates at period boundaries for preset mode
- Subscribes to entity state changes for entity mode
- Provides callbacks for dependent components to subscribe to horizon changes
"""

from collections.abc import Callable, Mapping
from datetime import datetime
import logging
from typing import Any, Literal

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.event import EventStateChangedData, async_track_point_in_time, async_track_state_change_event
from homeassistant.util import dt as dt_util

from custom_components.haeo.core.data.forecast_times import (
    extract_haeo_forecast_timestamps,
    generate_forecast_timestamps,
    periods_seconds_from_boundaries,
    tiers_to_periods_seconds,
)
from custom_components.haeo.core.schema.horizon_value import parse_horizon_config
from custom_components.haeo.core.state import EntityState

_LOGGER = logging.getLogger(__name__)


class _HassStateAdapter:
    """Adapt a Home Assistant State object to EntityState."""

    def __init__(self, entity_id: str, state: str, attributes: Mapping[str, Any]) -> None:
        self.entity_id = entity_id
        self.state = state
        self.attributes = attributes

    def as_dict(self) -> dict[str, Any]:
        return {"entity_id": self.entity_id, "state": self.state, "attributes": dict(self.attributes)}


class HorizonManager:
    """Manager for the forecast time horizon.

    This class:
    - Provides forecast timestamps for all input entities to use
    - Schedules updates at period boundaries (preset mode)
    - Listens for entity updates (entity mode)
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
        self._parsed_horizon = parse_horizon_config(config_entry.data)

        self._periods_seconds: list[int] = []
        self._smallest_period = 60
        self._unsub_timer: CALLBACK_TYPE | None = None
        self._unsub_state: CALLBACK_TYPE | None = None
        self._subscribers: list[Callable[[], None]] = []
        self._forecast_timestamps: tuple[float, ...] = ()

        self._update_timestamps()

    @property
    def horizon_mode(self) -> Literal["preset", "entity", "legacy_custom"]:
        """Return the configured horizon mode."""
        return self._parsed_horizon.mode

    @property
    def horizon_entity_id(self) -> str | None:
        """Return the configured horizon entity ID for entity mode."""
        return self._parsed_horizon.entity_id

    @property
    def horizon_preset(self) -> str | None:
        """Return the configured preset id for preset or legacy custom mode."""
        return self._parsed_horizon.preset

    def _entity_state(self) -> EntityState | None:
        """Return the configured horizon entity state when in entity mode."""
        entity_id = self._parsed_horizon.entity_id
        if entity_id is None:
            return None
        state = self._hass.states.get(entity_id)
        if state is None:
            return None
        return _HassStateAdapter(state.entity_id, state.state, state.attributes)

    def _update_timestamps(self) -> None:
        """Update cached periods and forecast timestamps from config or entity."""
        self._parsed_horizon = parse_horizon_config(self._config_entry.data)

        if self._parsed_horizon.mode == "entity":
            self._update_from_entity()
            return

        self._periods_seconds = tiers_to_periods_seconds(self._config_entry.data)
        if not self._periods_seconds:
            self._forecast_timestamps = ()
            self._smallest_period = 60
            return

        self._smallest_period = min(self._periods_seconds)
        self._forecast_timestamps = generate_forecast_timestamps(self._periods_seconds)

    def _update_from_entity(self) -> None:
        """Load periods and timestamps from the configured HAEO-format entity."""
        entity_state = self._entity_state()
        if entity_state is None:
            self._periods_seconds = []
            self._forecast_timestamps = ()
            self._smallest_period = 60
            return

        try:
            timestamps = extract_haeo_forecast_timestamps(entity_state)
            self._forecast_timestamps = timestamps
            self._periods_seconds = periods_seconds_from_boundaries(timestamps)
            self._smallest_period = min(self._periods_seconds)
        except ValueError:
            _LOGGER.warning(
                "Horizon entity %s has invalid forecast data; keeping previous horizon",
                entity_state.entity_id,
            )

    def start(self) -> Callable[[], None]:
        """Start scheduled updates or entity listening.

        Returns:
            A stop function that can be passed to async_on_unload.

        """
        if self._parsed_horizon.mode == "entity" and self._parsed_horizon.entity_id:
            self._unsub_state = async_track_state_change_event(
                self._hass,
                [self._parsed_horizon.entity_id],
                self._async_entity_state_changed,
            )
        else:
            self._schedule_next_update()
        return self.stop

    def stop(self) -> None:
        """Stop scheduled updates and clean up resources."""
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None
        if self._unsub_state is not None:
            self._unsub_state()
            self._unsub_state = None
        self._subscribers.clear()

    def pause(self) -> None:
        """Pause scheduled updates without clearing subscribers."""
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None

    def resume(self) -> None:
        """Resume updates after being paused."""
        self._update_timestamps()

        for subscriber in self._subscribers:
            subscriber()

        if self._parsed_horizon.mode == "entity":
            return
        self._schedule_next_update()

    def _schedule_next_update(self) -> None:
        """Schedule the next horizon update at the next period boundary."""
        if not self._periods_seconds:
            return

        now = dt_util.utcnow()
        epoch_seconds = now.timestamp()

        current_boundary = epoch_seconds // self._smallest_period * self._smallest_period
        next_boundary = current_boundary + self._smallest_period

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

        for subscriber in self._subscribers:
            subscriber()

        self._schedule_next_update()

    @callback
    def _async_entity_state_changed(self, _event: Event[EventStateChangedData]) -> None:
        """Handle horizon source entity state changes."""
        self._update_timestamps()

        for subscriber in self._subscribers:
            subscriber()

    def subscribe(self, callback_fn: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to horizon changes."""
        self._subscribers.append(callback_fn)

        def unsubscribe() -> None:
            if callback_fn in self._subscribers:
                self._subscribers.remove(callback_fn)

        return unsubscribe

    def get_forecast_timestamps(self) -> tuple[float, ...]:
        """Get the current forecast timestamps as epoch values."""
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
