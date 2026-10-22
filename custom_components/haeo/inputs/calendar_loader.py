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
from collections.abc import Callable, Coroutine
from datetime import UTC, date, datetime
import logging
from typing import TYPE_CHECKING, Final

from homeassistant.components.calendar import CalendarEntity
from homeassistant.components.calendar.const import DOMAIN as CALENDAR_DOMAIN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from custom_components.haeo.core.annotated_state import AnnotatedStateMachine, CalendarStateMachine, is_calendar_entity
from custom_components.haeo.core.data.loader.calendar import (
    CalendarEventData,
    EventValueText,
    capture_calendar_events,
    load_calendar_events,
    open_window_start,
    rejected_events,
)
from custom_components.haeo.core.data.util.field_units import field_unit_label
from custom_components.haeo.core.state import StateMachine
from custom_components.haeo.inputs.ha_state_machine import HomeAssistantStateMachine
from custom_components.haeo.inputs.meter_history import MeterHistory
from custom_components.haeo.repairs import create_calendar_event_values_issue, dismiss_calendar_event_values_issue

if TYPE_CHECKING:
    from homeassistant.core import Event
    from homeassistant.helpers.event import EventStateChangedData

    from custom_components.haeo.core.data.input_store import InputStore
    from custom_components.haeo.core.data.loader.calendar import CalendarEventDict
    from custom_components.haeo.horizon import HorizonManager
    from custom_components.haeo.input_stores import InputStoreKey, InputStoreMap

_LOGGER = logging.getLogger(__name__)


def is_calendar_driven(store: InputStore) -> bool:
    """Return True when any of a store's sources is a calendar, so the calendar loader loads it."""
    return any(is_calendar_entity(entity_id) for entity_id in store.source_entity_ids)


def _as_datetime(value: datetime | date) -> datetime:
    """Convert calendar event boundaries (datetime or all-day date) to datetime."""
    if isinstance(value, datetime):
        return value
    return dt_util.start_of_local_day(value)


# Longest event text quoted in the repair issue, so a long description does not swamp it
_QUOTED_TEXT_LENGTH: Final = 60


def _one_line(text: str) -> str:
    """Return text on one line, shortened with an ellipsis when it is long."""
    text = " ".join(text.split())
    return text if len(text) <= _QUOTED_TEXT_LENGTH else f"{text[: _QUOTED_TEXT_LENGTH - 1].rstrip()}…"


def _ignored_event_line(event: CalendarEventData, value_text: EventValueText) -> str:
    """Describe an ignored event by its start, its summary, and the text its value was read from.

    For example: ``2026-10-22T10:00:00+11:00 Pool pump — "Run 2 kW or 3 kW"``.
    """
    name = f" {_one_line(event.summary)}" if event.summary and value_text.field != "summary" else ""
    return f'{event.start.isoformat()}{name} — "{_one_line(value_text.text)}"'


class CalendarInputLoader:
    """Keeps inputs with a calendar source loaded with the calendars' upcoming events.

    A calendar's state carries no events, so these inputs cannot load from it
    directly. The loader fetches each calendar's events over the horizon,
    keeps them with the horizon they were fetched for, and loads the inputs
    through a state machine that injects them. It fetches again when a
    calendar changes or the horizon moves, and loads again from the kept
    events when another source of such an input changes.

    A meter input reads its window calendar, so it loads here too. The loader
    keeps its meters' running totals and injects them beside the events, so
    the input's captured source states hold everything it resolved from.
    """

    def __init__(
        self, hass: HomeAssistant, entry_id: str, stores: InputStoreMap, horizon_manager: HorizonManager
    ) -> None:
        """Initialize the loader over a prebuilt store map."""
        self._hass = hass
        self._entry_id = entry_id
        self._horizon_manager = horizon_manager
        self._stores: dict[InputStoreKey, InputStore] = {
            key: store for key, store in stores.items() if is_calendar_driven(store)
        }
        self._calendars = sorted(
            {eid for store in self._stores.values() for eid in store.source_entity_ids if is_calendar_entity(eid)}
        )
        self._meters = MeterHistory(
            hass,
            sorted(
                {
                    eid
                    for store in self._stores.values()
                    if store.hint.meter is not None
                    for eid in store.source_entity_ids
                    if not is_calendar_entity(eid)
                }
            ),
        )
        self._events: dict[str, list[CalendarEventDict] | None] = {}
        self._events_horizon: tuple[float, ...] = ()
        self._unsubs: list[Callable[[], None]] = []
        self._load_lock = asyncio.Lock()
        self._tasks: set[asyncio.Task[None]] = set()

    @callback
    def start(self) -> None:
        """Subscribe to change sources and schedule the initial load.

        The initial load runs in the background, so a slow calendar backend
        cannot block setup; setup waits for the stores with its own timeout.
        """
        if not self._stores:
            return

        other_sources = sorted(
            {eid for store in self._stores.values() for eid in store.source_entity_ids if not is_calendar_entity(eid)}
        )

        @callback
        def _on_calendar_change(_event: Event[EventStateChangedData]) -> None:
            self._schedule(self.async_load_all())

        @callback
        def _on_source_change(event: Event[EventStateChangedData]) -> None:
            self._meters.record(event.data["entity_id"], event.data["new_state"])
            self._schedule(self.async_resolve())

        self._unsubs.append(async_track_state_change_event(self._hass, self._calendars, _on_calendar_change))
        if other_sources:
            self._unsubs.append(async_track_state_change_event(self._hass, other_sources, _on_source_change))
        self._unsubs.append(self._horizon_manager.subscribe(lambda: self._schedule(self.async_load_all())))

        self._schedule(self._async_start())

    async def _async_start(self) -> None:
        """Read the meters' recorded totals, then load every store.

        The totals are read under the load lock, so no store resolves
        before its meters carry them.
        """
        async with self._load_lock:
            await self._meters.async_load()
        await self.async_load_all()

    @callback
    def _schedule(self, load: Coroutine[object, object, None]) -> None:
        """Start a reload that cleanup cancels if it is still running."""
        task = self._hass.async_create_task(load)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def async_load_all(self) -> None:
        """Fetch events for every calendar, then reload all stores together.

        A calendar whose fetch fails reads as unavailable rather than empty,
        so its stores become unavailable and optimization stops until a fetch
        succeeds, as it does for any other unavailable input.

        Overlapping calls run one at a time in the order they were made, so
        an older fetch never overwrites the stores after a newer one. Events
        are only kept for the horizon they were fetched for: when the horizon
        moves during the fetch, the reload it scheduled replaces this one.
        """
        async with self._load_lock:
            timestamps = self._horizon_manager.get_forecast_timestamps()
            fetched = await asyncio.gather(*(self._async_fetch_events(entity_id) for entity_id in self._calendars))
            if self._horizon_manager.get_forecast_timestamps() == timestamps:
                self._events = dict(zip(self._calendars, fetched, strict=True))
                self._events_horizon = timestamps
                self._resolve_stores()

    async def async_resolve(self) -> None:
        """Reload all stores from the kept events, after another source changed.

        When the horizon has moved since the events were fetched, the reload
        the move scheduled resolves the stores instead.
        """
        async with self._load_lock:
            if self._events_horizon == self._horizon_manager.get_forecast_timestamps():
                self._resolve_stores()

    def _resolve_stores(self) -> None:
        """Resolve every store, then notify the ones that changed.

        Every store resolves before any store notifies its listeners, so a
        listener never runs while another store still holds stale events.
        Stores whose value changed, that rejected their value, or that stopped
        being available notify, so a failed fetch stops optimization rather
        than leaving the last plan in place, and an unchanged fetch does not
        re-optimize.
        """
        calendars = CalendarStateMachine(HomeAssistantStateMachine(self._hass), self._events)
        sm = AnnotatedStateMachine(calendars, self._meters.attributes(self._meters_read_since(calendars)))
        changed = [store for store in self._stores.values() if store.resolve_from_sources(sm)]
        for store in changed:
            store.notify_listeners()
        self._report_ignored_event_values(sm)

    def _meters_read_since(self, calendars: StateMachine) -> dict[str, float | None]:
        """Return when each meter is read since: the earliest start of the windows open at the horizon start.

        A meter input measures its meters from the window its calendars have
        open at the horizon start. A meter read by no open window is read
        since no time.
        """
        at = datetime.fromtimestamp(self._horizon_manager.get_forecast_timestamps()[0], tz=UTC)
        since: dict[str, float | None] = {}
        for store in self._stores.values():
            if store.hint.meter is None:
                continue
            events = [
                event
                for eid in store.source_entity_ids
                if is_calendar_entity(eid)
                for event in load_calendar_events(calendars.get(eid), calendars.time_zone) or []
            ]
            opened = open_window_start(events, at)
            for eid in store.source_entity_ids:
                if is_calendar_entity(eid):
                    continue
                known = since.get(eid)
                since[eid] = opened if known is None else known if opened is None else min(known, opened)
        return since

    def _report_ignored_event_values(self, sm: StateMachine) -> None:
        """Raise a repair issue for each input ignoring calendar events whose values it cannot use.

        Only inputs reading event values in a unit, a forecast or the events'
        due amounts, can ignore one; window flags and meters do not read them.
        The due amounts report for the opened amounts too, as both read the
        same values.
        """
        reading_values = {
            key: (store, unit)
            for key, store in self._stores.items()
            if (unit := field_unit_label(store.hint.output_type)) is not None
            and store.hint.meter is None
            and (store.hint.calendar is None or store.hint.calendar.projection == "event_due")
        }
        for (element_name, field_path), (store, unit) in reading_values.items():
            calendars = [eid for eid in store.source_entity_ids if is_calendar_entity(eid)]
            ignored = [
                _ignored_event_line(event, value_text)
                for eid in calendars
                for event, value_text in rejected_events(
                    load_calendar_events(sm.get(eid), sm.time_zone) or [], store.hint.output_type
                )
            ]
            if ignored:
                create_calendar_event_values_issue(
                    self._hass,
                    self._entry_id,
                    element_name,
                    field_path,
                    calendars=calendars,
                    events=ignored,
                    unit=unit,
                )
            else:
                dismiss_calendar_event_values_issue(self._hass, self._entry_id, element_name, field_path)

    async def _async_fetch_events(self, entity_id: str) -> list[CalendarEventDict] | None:
        """Fetch the calendar's events over the current horizon, or None when it cannot be queried."""
        timestamps = self._horizon_manager.get_forecast_timestamps()
        return await async_fetch_calendar_events(
            self._hass,
            entity_id,
            datetime.fromtimestamp(timestamps[0], tz=UTC),
            datetime.fromtimestamp(timestamps[-1], tz=UTC),
        )

    def cleanup(self) -> None:
        """Unsubscribe from all change sources and cancel running reloads."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        for task in self._tasks:
            task.cancel()


async def async_fetch_calendar_events(
    hass: HomeAssistant, entity_id: str, start: datetime, end: datetime
) -> list[CalendarEventDict] | None:
    """Fetch a calendar's events between two times, serialized for the core loader.

    Calendars answer for past ranges as well as future ones, so the same fetch
    serves historical diagnostics. Returns None when the calendar entity cannot
    be queried (integration not loaded, entity missing, or the query failed).
    """
    component = hass.data.get(CALENDAR_DOMAIN)
    if not isinstance(component, EntityComponent):
        _LOGGER.debug("Calendar integration not loaded; no events for %s", entity_id)
        return None
    entity = component.get_entity(entity_id)
    if not isinstance(entity, CalendarEntity):
        _LOGGER.debug("Calendar entity %s not found; no events injected", entity_id)
        return None

    # Calendars match floating event times (no timezone, as create_event and
    # many imported calendars store them) in the query's timezone, so ask in
    # local time, which is what a floating time means in Home Assistant
    local_tz = dt_util.get_default_time_zone()
    try:
        calendar_events = await entity.async_get_events(hass, start.astimezone(local_tz), end.astimezone(local_tz))
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


__all__ = [
    "CalendarInputLoader",
    "async_fetch_calendar_events",
    "is_calendar_driven",
]
