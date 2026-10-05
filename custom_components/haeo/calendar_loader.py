"""Load calendar-driven input stores by fetching upcoming calendar events.

Home Assistant calendar entities only expose the current/next event in their
state, so the core calendar loader cannot see the full horizon by itself.
This module fetches upcoming events through the calendar integration's
``async_get_events`` API and presents them to the core loader by wrapping the
state machine so the calendar entity's state carries a ``haeo_events``
attribute — the exact format captured for diagnostics replay.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.calendar import CalendarEntity
from homeassistant.components.calendar.const import DOMAIN as CALENDAR_DOMAIN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from custom_components.haeo.core.data.loader.calendar import CalendarEventData, capture_calendar_events
from custom_components.haeo.core.state import EntityState, StateMachine
from custom_components.haeo.ha_state_machine import HomeAssistantStateMachine

if TYPE_CHECKING:
    from homeassistant.core import Event
    from homeassistant.helpers.event import EventStateChangedData

    from custom_components.haeo.core.data.input_store import InputStore
    from custom_components.haeo.core.schema.calendar_value import CalendarEventDict
    from custom_components.haeo.horizon import HorizonManager
    from custom_components.haeo.input_stores import InputStoreMap

_LOGGER = logging.getLogger(__name__)

CALENDAR_EVENTS_ATTRIBUTE = "haeo_events"


class _CalendarEventState:
    """EntityState wrapper that injects fetched events into attributes."""

    def __init__(self, base: EntityState, events: list[CalendarEventDict]) -> None:
        self._base = base
        self._events = events

    @property
    def entity_id(self) -> str:
        """Entity identifier."""
        return self._base.entity_id

    @property
    def state(self) -> str:
        """Raw state string."""
        return self._base.state

    @property
    def attributes(self) -> Mapping[str, Any]:
        """Entity attributes with fetched events merged in."""
        return {**self._base.attributes, CALENDAR_EVENTS_ATTRIBUTE: self._events}

    def as_dict(self) -> dict[str, Any]:
        """Return serialized state representation including the events."""
        base = self._base.as_dict()
        attributes = dict(base.get("attributes", {}))
        attributes[CALENDAR_EVENTS_ATTRIBUTE] = self._events
        return {**base, "attributes": attributes}


class CalendarStateMachine(StateMachine):
    """State machine decorator that augments calendar entities with events.

    Calendars mapped to None had their events fetch fail, so they read as
    unavailable rather than as an empty calendar.
    """

    def __init__(self, base: StateMachine, events_by_entity: Mapping[str, list[CalendarEventDict] | None]) -> None:
        """Initialize with a base state machine and per-entity event lists."""
        self._base = base
        self._events_by_entity = events_by_entity

    def get(self, entity_id: str) -> EntityState | None:
        """Return the entity state, with events merged for known calendars."""
        state = self._base.get(entity_id)
        if state is None or entity_id not in self._events_by_entity:
            return state
        events = self._events_by_entity[entity_id]
        if events is None:
            return None
        return _CalendarEventState(state, events)


def _as_datetime(value: datetime | date) -> datetime:
    """Convert calendar event boundaries (datetime or all-day date) to datetime."""
    if isinstance(value, datetime):
        return value
    return dt_util.start_of_local_day(value)


class CalendarInputLoader:
    """Keeps calendar-driven input stores loaded with upcoming events.

    Performs the initial load for every calendar-kind store and reloads on
    calendar entity state changes and horizon updates, so trip windows stay
    aligned with the optimization horizon as time advances.
    """

    def __init__(self, hass: HomeAssistant, stores: InputStoreMap, horizon_manager: HorizonManager) -> None:
        """Initialize the loader over a prebuilt store map."""
        self._hass = hass
        self._horizon_manager = horizon_manager
        self._stores: list[InputStore] = [store for store in stores.values() if store.source_kind == "calendar"]
        self._unsubs: list[Callable[[], None]] = []

    async def async_start(self) -> None:
        """Subscribe to change sources and perform the initial load."""
        if not self._stores:
            return

        entity_ids = sorted({eid for store in self._stores for eid in store.source_entity_ids})

        @callback
        def _on_state_change(_event: Event[EventStateChangedData]) -> None:
            self._hass.async_create_task(self.async_load_all())

        @callback
        def _on_horizon_change() -> None:
            self._hass.async_create_task(self.async_load_all())

        self._unsubs.append(async_track_state_change_event(self._hass, entity_ids, _on_state_change))
        self._unsubs.append(self._horizon_manager.subscribe(_on_horizon_change))

        await self.async_load_all()

    async def async_load_all(self) -> None:
        """Fetch events for every calendar, then reload all stores together.

        Every store resolves before any store notifies its listeners, so a
        listener never runs while another store still holds stale events.
        A calendar whose fetch fails reads as unavailable, so its stores keep
        their previous value instead of loading an empty calendar.
        """
        entity_ids = sorted({store.source_entity_ids[0] for store in self._stores})
        fetched = await asyncio.gather(*(self._async_fetch_events(entity_id) for entity_id in entity_ids))
        sm = CalendarStateMachine(HomeAssistantStateMachine(self._hass), dict(zip(entity_ids, fetched, strict=True)))
        loaded = [store for store in self._stores if store.resolve_from_sources(sm)]
        for store in loaded:
            store.notify_listeners()

    async def _async_fetch_events(self, entity_id: str) -> list[CalendarEventDict] | None:
        """Fetch upcoming events over the horizon, serialized for the core loader.

        Returns None when the calendar entity cannot be queried (integration not
        loaded, entity missing, or the query failed).
        """
        timestamps = self._horizon_manager.get_forecast_timestamps()
        if not timestamps:
            return None
        start = datetime.fromtimestamp(timestamps[0], tz=UTC)
        end = datetime.fromtimestamp(timestamps[-1], tz=UTC)

        component = self._hass.data.get(CALENDAR_DOMAIN)
        if not isinstance(component, EntityComponent):
            _LOGGER.debug("Calendar integration not loaded; no events for %s", entity_id)
            return None
        entity = component.get_entity(entity_id)
        if not isinstance(entity, CalendarEntity):
            _LOGGER.debug("Calendar entity %s not found; no events injected", entity_id)
            return None

        try:
            calendar_events = await entity.async_get_events(self._hass, start, end)
        except Exception:
            _LOGGER.warning("Failed to fetch events from %s", entity_id, exc_info=True)
            return None

        events = [
            CalendarEventData(
                start=_as_datetime(event.start),
                end=_as_datetime(event.end),
                summary=event.summary,
                location=event.location,
                description=event.description,
            )
            for event in calendar_events
        ]
        return capture_calendar_events(events)

    def cleanup(self) -> None:
        """Unsubscribe from all change sources."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()


__all__ = ["CALENDAR_EVENTS_ATTRIBUTE", "CalendarInputLoader", "CalendarStateMachine"]
