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
from collections.abc import Callable, Coroutine, Mapping
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


# How far past the horizon's end a fetch reaches, so horizon rolls resolve from
# the events already fetched rather than waiting on the calendar
CALENDAR_FETCH_AHEAD: Final = 86400.0

# Longest a calendar's events are waited for. Nothing waits on a fetch, so this
# only bounds how long a backend that never answers holds one open
CALENDAR_FETCH_TIMEOUT: Final = 300

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
    directly. The loader fetches each calendar's events from the horizon's
    start to a day past its end, keeps them with the span they cover, and
    loads the inputs through a state machine that injects them.

    A horizon roll resolves the inputs at once from the kept events, before the
    coordinator hears of it, so it never waits on a calendar, and then fetches
    the calendars again in the background to pick up any events added since.
    They are also fetched when one of them changes. A calendar whose fetch
    fails keeps its events while they still cover the horizon, and reads as
    unavailable once they do not.

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
        # Each calendar's kept events, and the span of time they cover
        self._events: dict[str, list[CalendarEventDict]] = {}
        self._covered: dict[str, tuple[float, float]] = {}
        # Fetches are numbered as they start, so an older one never overwrites a newer one's events
        self._fetches_started = 0
        self._fetch_applied = 0
        self._refreshing = False
        # The stores resolve once the meters' recorded totals have been read
        self._ready = False
        self._meters_retry: asyncio.Task[None] | None = None
        self._unsubs: list[Callable[[], None]] = []
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
            self.resolve()

        self._unsubs.append(async_track_state_change_event(self._hass, self._calendars, _on_calendar_change))
        if other_sources:
            self._unsubs.append(async_track_state_change_event(self._hass, other_sources, _on_source_change))
        self._unsubs.append(self._horizon_manager.subscribe(self._on_horizon_change))

        self._schedule(self._async_start())

    async def _async_start(self) -> None:
        """Read the meters' recorded totals, then fetch the calendars and load every store."""
        await self._meters.async_load()
        self._ready = True
        await self.async_load_all()

    @callback
    def _on_horizon_change(self) -> None:
        """Resolve the stores over the new horizon from the kept events, then fetch again in the background.

        Only one such refresh runs at a time, so a calendar that never answers
        holds one fetch rather than one per horizon roll.
        """
        self.resolve()
        if not self._refreshing:
            self._schedule(self._async_refresh())

    async def _async_refresh(self) -> None:
        """Fetch the calendars again in the background."""
        self._refreshing = True
        try:
            await self.async_load_all()
        finally:
            self._refreshing = False

    @callback
    def _schedule(self, load: Coroutine[object, object, None]) -> asyncio.Task[None]:
        """Start a background load that cleanup cancels if it is still running."""
        task = self._hass.async_create_task(load)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def async_load_all(self) -> None:
        """Fetch every calendar's events from the horizon start to a day past its end, then resolve the stores.

        A calendar whose fetch fails keeps the events it already has. Fetches
        can overlap, and one that finishes after a newer one has been applied
        is dropped, so the stores never go back to older events.

        When the meters' recorded totals could not be read at start, each load
        starts one retry in the background, which resolves the stores again
        once the totals are read; loads never wait on it.
        """
        if not self._meters.recorded and self._meters_retry is None:
            # Nothing waits on the retry, which has no timeout, so it runs as a background task
            self._meters_retry = self._hass.async_create_background_task(
                self._async_retry_meters(), f"haeo_meter_retry_{self._entry_id}"
            )
            self._tasks.add(self._meters_retry)
            self._meters_retry.add_done_callback(self._tasks.discard)
        self._fetches_started += 1
        fetch = self._fetches_started
        timestamps = self._horizon_manager.get_forecast_timestamps()
        span = (timestamps[0], timestamps[-1] + CALENDAR_FETCH_AHEAD)
        fetched = await asyncio.gather(*(self._async_fetch_events(entity_id, span) for entity_id in self._calendars))
        if fetch < self._fetch_applied:
            return
        self._fetch_applied = fetch
        for entity_id, events in zip(self._calendars, fetched, strict=True):
            if events is not None:
                self._events[entity_id] = events
                self._covered[entity_id] = span
        self.resolve()

    async def _async_retry_meters(self) -> None:
        """Read the meters' recorded totals again, then resolve the stores with them.

        The read has no timeout, since nothing waits on it, so a recorder that
        does not answer holds one read rather than one per load.
        """
        try:
            await self._meters.async_retry()
        finally:
            self._meters_retry = None
        if self._meters.recorded:
            self.resolve()

    @callback
    def resolve(self) -> None:
        """Resolve every store over the current horizon from the kept events.

        A calendar whose kept events do not cover the horizon reads as
        unavailable, so its stores stop optimization until a fetch covers it.
        """
        if not self._ready:
            return
        timestamps = self._horizon_manager.get_forecast_timestamps()
        events = {
            entity_id: self._events[entity_id]
            if (covered := self._covered.get(entity_id)) is not None
            and covered[0] <= timestamps[0]
            and timestamps[-1] <= covered[1]
            else None
            for entity_id in self._calendars
        }
        self._resolve_stores(events)

    def _resolve_stores(self, events: Mapping[str, list[CalendarEventDict] | None]) -> None:
        """Resolve every store, then notify the ones that changed.

        Every store resolves before any store notifies its listeners, so a
        listener never runs while another store still holds stale events.
        Stores whose value changed, that rejected their value, or that stopped
        being available notify, so a failed fetch stops optimization rather
        than leaving the last plan in place, and an unchanged fetch does not
        re-optimize.
        """
        calendars = CalendarStateMachine(HomeAssistantStateMachine(self._hass), events)
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

    async def _async_fetch_events(self, entity_id: str, span: tuple[float, float]) -> list[CalendarEventDict] | None:
        """Fetch the calendar's events over a span of time, or None when it cannot be queried."""
        return await async_fetch_calendar_events(
            self._hass,
            entity_id,
            datetime.fromtimestamp(span[0], tz=UTC),
            datetime.fromtimestamp(span[1], tz=UTC),
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
    be queried (integration not loaded, entity missing, or the query failed or
    took longer than ``CALENDAR_FETCH_TIMEOUT``).
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
        async with asyncio.timeout(CALENDAR_FETCH_TIMEOUT):
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
