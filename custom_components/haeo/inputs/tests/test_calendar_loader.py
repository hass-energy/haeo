"""Tests for the calendar input loader."""

import asyncio
from collections.abc import Callable
from datetime import UTC, date, datetime
import logging
from unittest.mock import Mock, patch

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.components.calendar.const import DOMAIN as CALENDAR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.util import dt as dt_util
import numpy as np
import pytest

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.data.input_store import InputStore, create_input_store
from custom_components.haeo.core.data.loader.calendar import CALENDAR_EVENTS_ATTRIBUTE
from custom_components.haeo.core.data.loader.meter import METER_TOTALS_ATTRIBUTE
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.field_hints import FieldHint, MeterFieldHint, calendar_input
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.inputs.calendar_loader import CalendarInputLoader

_LOGGER = logging.getLogger(__name__)

FORECAST_TIMESTAMPS: tuple[float, ...] = (0.0, 3600.0, 7200.0)

ENTITY_ID = "calendar.trips"


class _MemStorage:
    """In-memory storage double implementing the Storage protocol."""

    def __init__(self, value: object) -> None:
        self.value = value

    async def write(self, value: object) -> None:
        self.value = value


def _calendar_store(
    entity_id: str = ENTITY_ID,
    get_forecast_timestamps: Callable[[], tuple[float, ...]] = lambda: FORECAST_TIMESTAMPS,
) -> InputStore:
    """Build a store for a calendar input reading a calendar entity's presence."""
    return create_input_store(
        value={"type": "entity", "value": [entity_id]},
        storage=_MemStorage({"type": "entity", "value": [entity_id]}),
        hint=calendar_input(OutputType.AVAILABILITY, "window_active"),
        get_forecast_timestamps=get_forecast_timestamps,
    )


def _presence(store: InputStore) -> np.ndarray:
    """Return the resolved per-period presence of a loaded calendar store."""
    value = store.value
    assert isinstance(value, np.ndarray)
    return value


def _trip(start_ts: float, end_ts: float) -> CalendarEvent:
    """Build a calendar event spanning the given epoch seconds."""
    return CalendarEvent(
        start=datetime.fromtimestamp(start_ts, tz=UTC),
        end=datetime.fromtimestamp(end_ts, tz=UTC),
        summary="Trip",
    )


def _demand(start_ts: float, end_ts: float, summary: str) -> CalendarEvent:
    """Build a calendar event holding a number in its summary."""
    return CalendarEvent(
        start=datetime.fromtimestamp(start_ts, tz=UTC),
        end=datetime.fromtimestamp(end_ts, tz=UTC),
        summary=summary,
    )


@pytest.fixture
def horizon_manager() -> Mock:
    """Return a mock horizon manager with fixed timestamps."""
    manager = Mock(spec=HorizonManager)
    manager.get_forecast_timestamps.return_value = FORECAST_TIMESTAMPS
    manager.subscribe.return_value = Mock()
    return manager


def _overlapping(events: list[CalendarEvent], start: datetime, end: datetime) -> list[CalendarEvent]:
    """Return the events overlapping a range, as a calendar's fetch does."""
    return [event for event in events if event.end_datetime_local > start and event.start_datetime_local < end]


class _StubCalendar(CalendarEntity):
    """Calendar entity double returning canned events."""

    _attr_has_entity_name = False

    def __init__(self, events: list[CalendarEvent], name: str = "Trips") -> None:
        self._attr_name = name
        self._events = events
        self.fail = False
        self.fetches = 0

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        return self._events[0] if self._events else None

    async def async_get_events(
        self,
        hass: HomeAssistant,  # noqa: ARG002 (signature fixed by CalendarEntity)
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return the canned events overlapping the range, yielding like a real fetch."""
        self.fetches += 1
        await asyncio.sleep(0)
        if self.fail:
            msg = "Calendar backend unreachable"
            raise HomeAssistantError(msg)
        return _overlapping(self._events, start_date, end_date)


async def _add_stub_calendars(hass: HomeAssistant, *calendars: _StubCalendar) -> None:
    """Register stub calendar entities with the calendar component."""
    component: EntityComponent[CalendarEntity] = EntityComponent(_LOGGER, CALENDAR_DOMAIN, hass)
    hass.data[CALENDAR_DOMAIN] = component
    await component.async_add_entities(list(calendars))
    await hass.async_block_till_done()


async def _add_stub_calendar(hass: HomeAssistant, events: list[CalendarEvent]) -> _StubCalendar:
    """Register a stub calendar entity under calendar.trips."""
    calendar = _StubCalendar(events)
    await _add_stub_calendars(hass, calendar)
    return calendar


# --- CalendarInputLoader ---


async def test_loader_fetches_events_and_loads_store(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """The loader fetches calendar events and resolves the store."""
    await _add_stub_calendar(
        hass,
        [
            CalendarEvent(
                start=datetime.fromtimestamp(0.0, tz=UTC),
                end=datetime.fromtimestamp(3600.0, tz=UTC),
                summary="Trip",
            )
        ],
    )
    store = _calendar_store()
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_calendar")): store}, horizon_manager)

    loader.start()
    await hass.async_block_till_done()

    assert store.available
    np.testing.assert_allclose(_presence(store), [1.0, 0.0])
    loader.cleanup()


async def test_loader_without_calendar_component_leaves_store_unavailable(
    hass: HomeAssistant,
    horizon_manager: Mock,
) -> None:
    """Without the calendar integration the store cannot load."""
    store = _calendar_store()
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_calendar")): store}, horizon_manager)

    loader.start()
    await hass.async_block_till_done()

    assert not store.available
    loader.cleanup()


async def test_loader_reloads_on_calendar_state_change(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """A calendar entity state change triggers a reload."""
    await _add_stub_calendar(hass, [])
    store = _calendar_store()
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
    loader.start()
    await hass.async_block_till_done()
    np.testing.assert_allclose(_presence(store), [0.0, 0.0])

    component: EntityComponent[CalendarEntity] = hass.data[CALENDAR_DOMAIN]
    entity = component.get_entity(ENTITY_ID)
    assert isinstance(entity, _StubCalendar)
    entity._events = [
        CalendarEvent(
            start=datetime.fromtimestamp(3600.0, tz=UTC),
            end=datetime.fromtimestamp(7200.0, tz=UTC),
            summary="Trip",
        )
    ]
    hass.states.async_set(ENTITY_ID, "on")
    await hass.async_block_till_done()

    np.testing.assert_allclose(_presence(store), [0.0, 1.0])
    loader.cleanup()


async def test_loader_without_calendar_stores_is_inert(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """A store map without calendar stores subscribes to nothing."""
    loader = CalendarInputLoader(hass, "entry_id", {}, horizon_manager)

    loader.start()
    await hass.async_block_till_done()

    horizon_manager.subscribe.assert_not_called()
    loader.cleanup()


async def test_failed_refresh_keeps_events_until_they_no_longer_cover_the_horizon(
    hass: HomeAssistant, horizon_manager: Mock
) -> None:
    """A failed fetch keeps planning from the events already fetched, until the horizon moves past them."""
    calendar = await _add_stub_calendar(hass, [_trip(0.0, 3600.0)])
    store = _calendar_store(get_forecast_timestamps=horizon_manager.get_forecast_timestamps)
    listener = Mock()
    store.add_listener(listener)
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
    loader.start()
    await hass.async_block_till_done()
    listener.reset_mock()

    calendar.fail = True
    await loader.async_load_all()
    assert store.available
    listener.assert_not_called()

    # Two days on, the events fetched no longer reach the end of the horizon
    horizon_manager.get_forecast_timestamps.return_value = tuple(t + 2 * 86400.0 for t in FORECAST_TIMESTAMPS)
    horizon_manager.subscribe.call_args.args[0]()
    await hass.async_block_till_done()

    assert not store.available
    listener.assert_called_once()
    loader.cleanup()


async def test_loader_unchanged_fetch_does_not_notify(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """Fetching the same events again does not tell listeners, so it does not re-optimize."""
    await _add_stub_calendar(hass, [_trip(0.0, 3600.0)])
    store = _calendar_store()
    listener = Mock()
    store.add_listener(listener)
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
    loader.start()
    await hass.async_block_till_done()
    listener.assert_called_once()
    listener.reset_mock()

    await loader.async_load_all()
    loader.resolve()

    assert store.available
    listener.assert_not_called()
    loader.cleanup()


class _HangingCalendar(_StubCalendar):
    """Calendar entity double whose backend can stop answering."""

    def __init__(self, events: list[CalendarEvent]) -> None:
        super().__init__(events)
        self.hangs = False

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Never answer while hanging, otherwise return the canned events."""
        if self.hangs:
            await asyncio.Event().wait()
        return await super().async_get_events(hass, start_date, end_date)


async def test_loader_recovers_from_a_calendar_that_stops_answering(
    hass: HomeAssistant, horizon_manager: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fetch that never returns times out and keeps the events already fetched, and a later fetch replaces them."""
    monkeypatch.setattr("custom_components.haeo.inputs.calendar_loader.CALENDAR_FETCH_TIMEOUT", 0.01)
    calendar = _HangingCalendar([_trip(0.0, 3600.0)])
    await _add_stub_calendars(hass, calendar)
    store = _calendar_store()
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
    loader.start()
    await hass.async_block_till_done()
    np.testing.assert_allclose(_presence(store), [1.0, 0.0])

    calendar.hangs = True
    await loader.async_load_all()
    assert store.available
    np.testing.assert_allclose(_presence(store), [1.0, 0.0])

    calendar.hangs = False
    calendar._events = [_trip(3600.0, 7200.0)]
    await loader.async_load_all()
    np.testing.assert_allclose(_presence(store), [0.0, 1.0])
    loader.cleanup()


async def test_loader_initial_fetch_failure_leaves_store_not_ready(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """A failed first fetch does not load the store as an empty calendar."""
    calendar = await _add_stub_calendar(hass, [_trip(0.0, 3600.0)])
    calendar.fail = True
    store = _calendar_store()
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_calendar")): store}, horizon_manager)

    loader.start()
    await hass.async_block_till_done()

    assert not store.is_ready()
    assert store.value is None
    loader.cleanup()


async def test_loader_replays_events_a_captured_state_carries(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """A replayed calendar state that already carries events resolves without a calendar to fetch from."""
    hass.states.async_set(
        ENTITY_ID,
        "on",
        {
            CALENDAR_EVENTS_ATTRIBUTE: [
                {
                    "start": "1970-01-01T00:00:00+00:00",
                    "end": "1970-01-01T01:00:00+00:00",
                    "summary": "Trip",
                    "location": None,
                    "description": None,
                }
            ]
        },
    )
    store = _calendar_store()
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_presence")): store}, horizon_manager)

    loader.start()
    await hass.async_block_till_done()

    np.testing.assert_allclose(_presence(store), [1.0, 0.0])
    loader.cleanup()


async def test_loader_reloads_all_stores_before_listeners_run(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """A store's listener sees every other store already reloaded."""
    await _add_stub_calendars(
        hass,
        _StubCalendar([_trip(0.0, 3600.0)], name="Trips"),
        _StubCalendar([_trip(3600.0, 7200.0)], name="Loads"),
    )
    trips = _calendar_store(ENTITY_ID)
    loads = _calendar_store("calendar.loads")
    observed: list[object] = []
    trips.add_listener(lambda: observed.append(loads.value))
    loader = CalendarInputLoader(
        hass,
        "entry_id",
        {("EV", ("trip", "trip_calendar")): trips, ("Load", ("window", "window_calendar")): loads},
        horizon_manager,
    )

    loader.start()
    await hass.async_block_till_done()

    assert len(observed) == 1
    assert observed[0] is loads.value
    np.testing.assert_allclose(_presence(loads), [0.0, 1.0])
    loader.cleanup()


async def test_loader_reloads_on_horizon_change(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """The horizon subscription reloads stores against the new boundaries."""
    await _add_stub_calendar(hass, [_trip(3600.0, 7200.0)])
    store = _calendar_store(get_forecast_timestamps=horizon_manager.get_forecast_timestamps)
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
    loader.start()
    await hass.async_block_till_done()
    np.testing.assert_allclose(_presence(store), [0.0, 1.0])

    new_timestamps = (3600.0, 7200.0, 10800.0)
    horizon_manager.get_forecast_timestamps.return_value = new_timestamps
    on_horizon_change = horizon_manager.subscribe.call_args.args[0]
    on_horizon_change()
    await hass.async_block_till_done()

    assert store.forecast_timestamps == new_timestamps
    np.testing.assert_allclose(_presence(store), [1.0, 0.0])
    loader.cleanup()


async def test_horizon_roll_resolves_from_the_events_already_fetched(
    hass: HomeAssistant, horizon_manager: Mock
) -> None:
    """A horizon roll moves calendar inputs at once from the events already fetched, then fetches in the background."""
    calendar = await _add_stub_calendar(hass, [_trip(3600.0, 7200.0)])
    store = _calendar_store(get_forecast_timestamps=horizon_manager.get_forecast_timestamps)
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
    loader.start()
    await hass.async_block_till_done()
    assert calendar.fetches == 1

    new_timestamps = (3600.0, 7200.0, 10800.0)
    horizon_manager.get_forecast_timestamps.return_value = new_timestamps
    horizon_manager.subscribe.call_args.args[0]()

    assert store.forecast_timestamps == new_timestamps
    np.testing.assert_allclose(_presence(store), [1.0, 0.0])
    assert calendar.fetches == 1

    # The fetch the roll started picks up an event added since
    calendar._events = [_trip(3600.0, 7200.0), _trip(7200.0, 10800.0)]
    await hass.async_block_till_done()
    assert calendar.fetches == 2
    np.testing.assert_allclose(_presence(store), [1.0, 1.0])
    loader.cleanup()


async def test_horizon_roll_does_not_wait_on_a_calendar_that_stopped_answering(
    hass: HomeAssistant, horizon_manager: Mock
) -> None:
    """While a refresh hangs, horizon rolls still move calendar inputs from the events already fetched."""
    calendar = _HangingCalendar([_trip(3600.0, 7200.0)])
    await _add_stub_calendars(hass, calendar)
    store = _calendar_store(get_forecast_timestamps=horizon_manager.get_forecast_timestamps)
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
    loader.start()
    await hass.async_block_till_done()

    calendar.hangs = True
    hanging = hass.async_create_task(loader.async_load_all())
    await asyncio.sleep(0)
    new_timestamps = (3600.0, 7200.0, 10800.0)
    horizon_manager.get_forecast_timestamps.return_value = new_timestamps
    horizon_manager.subscribe.call_args.args[0]()

    assert store.forecast_timestamps == new_timestamps
    np.testing.assert_allclose(_presence(store), [1.0, 0.0])
    hanging.cancel()
    loader.cleanup()


class _GatedCalendar(_StubCalendar):
    """Calendar double whose fetches each return their own events once their gate opens."""

    def __init__(self) -> None:
        super().__init__([])
        self.responses: list[tuple[list[CalendarEvent], asyncio.Event]] = []

    async def async_get_events(
        self,
        hass: HomeAssistant,  # noqa: ARG002 (signature fixed by CalendarEntity)
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return the next queued events overlapping the range after waiting for that fetch's gate."""
        events, gate = self.responses.pop(0)
        await gate.wait()
        return _overlapping(events, start_date, end_date)


async def test_loader_applies_overlapping_reloads_in_trigger_order(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """An older reload finishing after a newer one does not overwrite the store with stale events."""
    calendar = _GatedCalendar()
    await _add_stub_calendars(hass, calendar)
    store = _calendar_store()
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
    initial_gate = asyncio.Event()
    initial_gate.set()
    calendar.responses.append(([], initial_gate))
    loader.start()
    await hass.async_block_till_done()

    stale_gate = asyncio.Event()
    fresh_gate = asyncio.Event()
    fresh_gate.set()
    calendar.responses.append(([_trip(0.0, 3600.0)], stale_gate))
    calendar.responses.append(([_trip(3600.0, 7200.0)], fresh_gate))
    older = hass.async_create_task(loader.async_load_all())
    await asyncio.sleep(0)
    newer = hass.async_create_task(loader.async_load_all())
    for _ in range(5):
        await asyncio.sleep(0)
    stale_gate.set()
    await asyncio.gather(older, newer)

    np.testing.assert_allclose(_presence(store), [0.0, 1.0])
    loader.cleanup()


async def test_loader_serves_a_moved_horizon_from_a_fetch_that_covers_it(
    hass: HomeAssistant, horizon_manager: Mock
) -> None:
    """A fetch that finishes after the horizon moved still serves the new horizon, since it reaches past it."""
    calendar = _GatedCalendar()
    await _add_stub_calendars(hass, calendar)
    store = _calendar_store(get_forecast_timestamps=horizon_manager.get_forecast_timestamps)
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
    gate = asyncio.Event()
    calendar.responses.append(([_trip(3600.0, 7200.0)], gate))

    loader.start()
    await asyncio.sleep(0)
    horizon_manager.get_forecast_timestamps.return_value = (3600.0, 7200.0, 10800.0)
    gate.set()
    await hass.async_block_till_done()

    assert store.forecast_timestamps == (3600.0, 7200.0, 10800.0)
    np.testing.assert_allclose(_presence(store), [1.0, 0.0])
    loader.cleanup()


async def test_cleanup_cancels_running_reloads(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """A reload still waiting on its fetch is cancelled when the loader is cleaned up."""
    calendar = _GatedCalendar()
    await _add_stub_calendars(hass, calendar)
    store = _calendar_store()
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
    gate = asyncio.Event()
    calendar.responses.append(([_trip(0.0, 3600.0)], gate))
    loader.start()
    await asyncio.sleep(0)

    loader.cleanup()
    gate.set()
    await hass.async_block_till_done()

    assert not store.is_ready()


async def test_loader_sums_a_calendar_with_a_sensor_in_a_forecast_field(
    hass: HomeAssistant, horizon_manager: Mock
) -> None:
    """A forecast field reading a sensor and a calendar combines them, reloading when the sensor changes.

    The sensor's present value fills the first period, as it does beside any forecast.
    """
    # Real epoch times: stepped forecasts need them for their steps to survive forecast cycling
    start = 1_767_225_600.0
    timestamps = (start, start + 3600.0, start + 7200.0)
    horizon_manager.get_forecast_timestamps.return_value = timestamps
    calendar = await _add_stub_calendar(hass, [_demand(start + 3600.0, start + 7200.0, "2000 W")])

    def _set_base(value: float) -> None:
        hass.states.async_set("sensor.base", str(value), {"unit_of_measurement": "kW", "device_class": "power"})

    _set_base(1.0)
    store = create_input_store(
        value={"type": "entity", "value": ["sensor.base", ENTITY_ID]},
        storage=_MemStorage({"type": "entity", "value": ["sensor.base", ENTITY_ID]}),
        hint=FieldHint(output_type=OutputType.POWER, time_series=True),
        get_forecast_timestamps=lambda: timestamps,
    )
    loader = CalendarInputLoader(hass, "entry_id", {("Load", ("forecast", "forecast")): store}, horizon_manager)
    loader.start()
    await hass.async_block_till_done()
    np.testing.assert_allclose(_presence(store), [1.0, 2.0])

    calendar.fail = True
    _set_base(5.0)
    await hass.async_block_till_done()

    np.testing.assert_allclose(_presence(store), [5.0, 2.0])
    loader.cleanup()


def _forecast_store() -> InputStore:
    """Build a store for a power forecast field reading the calendar."""
    return create_input_store(
        value={"type": "entity", "value": [ENTITY_ID]},
        storage=_MemStorage({"type": "entity", "value": [ENTITY_ID]}),
        hint=FieldHint(output_type=OutputType.POWER, time_series=True),
        get_forecast_timestamps=lambda: FORECAST_TIMESTAMPS,
    )


ISSUE_ID = "calendar_event_values_entry_id_Load_forecast.forecast"


async def test_loader_raises_a_repair_for_event_values_an_input_ignores(
    hass: HomeAssistant, horizon_manager: Mock
) -> None:
    """An event whose value the input cannot use is ignored, raising a repair issue that clears once it is fixed."""
    pump = CalendarEvent(
        start=datetime.fromtimestamp(3600.0, tz=UTC),
        end=datetime.fromtimestamp(7200.0, tz=UTC),
        summary="Pool pump",
        description="Run 2 kW or 3 kW\nJoin the call at https://example.com/meeting/123456 to watch the pump run",
    )
    calendar = await _add_stub_calendar(hass, [_demand(0.0, 3600.0, "2"), _demand(3600.0, 7200.0, "3 kW"), pump])
    store = _forecast_store()
    loader = CalendarInputLoader(hass, "entry_id", {("Load", ("forecast", "forecast")): store}, horizon_manager)
    loader.start()
    await hass.async_block_till_done()

    assert store.available
    issue = ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ID)
    assert issue is not None
    assert issue.translation_placeholders is not None
    assert issue.translation_placeholders["events"] == (
        '- 1970-01-01T00:00:00+00:00 — "2"\n'
        '- 1970-01-01T01:00:00+00:00 Pool pump — "Run 2 kW or 3 kW Join the call at https://example.com/meeti…"'
    )
    assert issue.translation_placeholders["unit"] == "kW"

    calendar._events = [_demand(0.0, 3600.0, "2 kW")]
    await loader.async_load_all()

    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ID) is None
    loader.cleanup()


async def test_loader_raises_no_repair_for_window_flags(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """Window flags do not read event values, so an unusable value raises no repair issue for them."""
    await _add_stub_calendar(hass, [_demand(0.0, 3600.0, "2")])
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_away")): _calendar_store()}, horizon_manager)
    loader.start()
    await hass.async_block_till_done()

    assert not [issue_id for domain, issue_id in ir.async_get(hass).issues if domain == DOMAIN]
    loader.cleanup()


async def test_loader_reads_all_day_events_from_local_midnight(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """An all-day event covers its days from local midnight."""
    start = dt_util.start_of_local_day(datetime(2026, 1, 1, tzinfo=dt_util.get_default_time_zone()))
    timestamps = (start.timestamp() - 3600.0, start.timestamp(), start.timestamp() + 3600.0)
    horizon_manager.get_forecast_timestamps.return_value = timestamps
    await _add_stub_calendar(hass, [CalendarEvent(start=date(2026, 1, 1), end=date(2026, 1, 2), summary="Away")])
    store = _calendar_store(get_forecast_timestamps=lambda: timestamps)
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_away")): store}, horizon_manager)

    loader.start()
    await hass.async_block_till_done()

    np.testing.assert_allclose(_presence(store), [0.0, 1.0])
    loader.cleanup()


class _FloatingCalendar(_StubCalendar):
    """Calendar double storing floating times, read in the query's timezone as local_calendar does."""

    def __init__(self, floating: list[tuple[datetime, datetime]]) -> None:
        super().__init__([])
        self._floating = floating

    async def async_get_events(
        self,
        hass: HomeAssistant,  # noqa: ARG002 (signature fixed by CalendarEntity)
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Match floating times against the range in its own timezone, returning them as local times."""
        query_tz = start_date.tzinfo
        local_tz = dt_util.get_default_time_zone()
        return [
            CalendarEvent(start=start.replace(tzinfo=local_tz), end=end.replace(tzinfo=local_tz), summary="Trip")
            for start, end in self._floating
            if end.replace(tzinfo=query_tz) > start_date and start.replace(tzinfo=query_tz) < end_date
        ]


async def test_loader_fetches_floating_events_in_local_time(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """A floating event, as create_event and imported calendars store them, is matched to the horizon in local time."""
    await hass.config.async_set_time_zone("Australia/Sydney")
    local_tz = dt_util.get_default_time_zone()
    timestamps = tuple(datetime(2026, 10, 25, hour, tzinfo=local_tz).timestamp() for hour in (0, 6, 12))
    horizon_manager.get_forecast_timestamps.return_value = timestamps
    floating = (datetime(2026, 10, 25, 9), datetime(2026, 10, 25, 19, 30))  # noqa: DTZ001 (floating times have no zone)
    calendar = _FloatingCalendar([floating])
    await _add_stub_calendars(hass, calendar)
    store = _calendar_store(get_forecast_timestamps=lambda: timestamps)
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_away")): store}, horizon_manager)

    loader.start()
    await hass.async_block_till_done()

    np.testing.assert_allclose(_presence(store), [0.0, 1.0])
    loader.cleanup()


async def test_loader_leaves_a_store_unavailable_when_its_calendar_is_missing(
    hass: HomeAssistant, horizon_manager: Mock
) -> None:
    """A calendar the calendar integration does not know cannot be fetched, so its store stays unavailable."""
    await _add_stub_calendar(hass, [_trip(0.0, 3600.0)])
    store = _calendar_store("calendar.unknown")
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_away")): store}, horizon_manager)

    loader.start()
    await hass.async_block_till_done()

    assert not store.available
    loader.cleanup()


METER_ID = "sensor.pump_energy"


async def test_loader_resolves_a_meter_input_with_its_totals_beside_the_events(
    hass: HomeAssistant, horizon_manager: Mock
) -> None:
    """A meter input resolves to its meter's rise since the open window began, capturing the totals and the events."""
    start = dt_util.utcnow().timestamp()
    timestamps = (start, start + 3600.0)
    horizon_manager.get_forecast_timestamps.return_value = timestamps
    await _add_stub_calendar(hass, [_demand(start - 3600.0, start + 3600.0, "6 kWh")])
    hass.states.async_set(METER_ID, "10", {"unit_of_measurement": "kWh", "device_class": "energy"})
    sources = {"type": "entity", "value": [METER_ID, ENTITY_ID]}
    store = create_input_store(
        value=sources,
        storage=_MemStorage(sources),
        hint=FieldHint(output_type=OutputType.ENERGY, meter=MeterFieldHint(since="window_calendar")),
        get_forecast_timestamps=lambda: timestamps,
    )
    loader = CalendarInputLoader(hass, "entry_id", {("Pump", ("schedule", "energy_meter")): store}, horizon_manager)
    loader.start()
    await hass.async_block_till_done()
    assert store.value == pytest.approx(0.0)

    hass.states.async_set(METER_ID, "12.5", {"unit_of_measurement": "kWh", "device_class": "energy"})
    await hass.async_block_till_done()

    assert store.value == pytest.approx(2.5)
    captured = store.captured_source_states
    assert CALENDAR_EVENTS_ATTRIBUTE in captured[ENTITY_ID].attributes
    assert METER_TOTALS_ATTRIBUTE in captured[METER_ID].attributes
    assert (
        ir.async_get(hass).async_get_issue(DOMAIN, "calendar_event_values_entry_id_Pump_schedule.energy_meter") is None
    )
    loader.cleanup()


async def test_loader_reads_meter_totals_again_until_the_recorder_answers(
    hass: HomeAssistant, horizon_manager: Mock
) -> None:
    """A recorder read that fails at start is retried in the background, so the meter gets its recorded totals."""
    start = dt_util.utcnow().timestamp()
    timestamps = (start, start + 3600.0)
    horizon_manager.get_forecast_timestamps.return_value = timestamps
    await _add_stub_calendar(hass, [_demand(start - 3600.0, start + 3600.0, "6 kWh")])
    hass.config.components.add("recorder")
    hass.states.async_set(METER_ID, "12.5", {"unit_of_measurement": "kWh", "device_class": "energy"})
    sources = {"type": "entity", "value": [METER_ID, ENTITY_ID]}
    store = create_input_store(
        value=sources,
        storage=_MemStorage(sources),
        hint=FieldHint(output_type=OutputType.ENERGY, meter=MeterFieldHint(since="window_calendar")),
        get_forecast_timestamps=lambda: timestamps,
    )
    loader = CalendarInputLoader(hass, "entry_id", {("Pump", ("schedule", "energy_meter")): store}, horizon_manager)
    recorded = ([(start - 7200.0, 0.0), (start - 3600.0, 2.0)], 10.0)
    reads = iter([RuntimeError("database busy"), recorded])

    async def run(_func: Callable[..., object], *_args: object) -> object:
        result = next(reads)
        if isinstance(result, Exception):
            raise result
        return result

    recorder = Mock()
    recorder.async_add_executor_job = run
    with patch("custom_components.haeo.inputs.meter_history.get_instance", return_value=recorder):
        # The first load starts a retry in the background, which resolves the store once it reads the totals
        loader.start()
        await hass.async_block_till_done(wait_background_tasks=True)

    assert store.value == pytest.approx(2.5)
    loader.cleanup()


async def test_a_hung_recorder_does_not_hold_up_calendar_loads(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """While the meters' recorded totals cannot be read, calendar inputs still load on every reload without them."""
    start = dt_util.utcnow().timestamp()
    timestamps = (start, start + 3600.0)
    horizon_manager.get_forecast_timestamps.return_value = timestamps
    await _add_stub_calendar(hass, [_demand(start - 3600.0, start + 3600.0, "6 kWh")])
    hass.config.components.add("recorder")
    hass.states.async_set(METER_ID, "12.5", {"unit_of_measurement": "kWh", "device_class": "energy"})
    sources = {"type": "entity", "value": [METER_ID, ENTITY_ID]}
    store = create_input_store(
        value=sources,
        storage=_MemStorage(sources),
        hint=FieldHint(output_type=OutputType.ENERGY, meter=MeterFieldHint(since="window_calendar")),
        get_forecast_timestamps=lambda: timestamps,
    )
    loader = CalendarInputLoader(hass, "entry_id", {("Pump", ("schedule", "energy_meter")): store}, horizon_manager)
    reads = 0

    async def hang(_func: Callable[..., object], *_args: object) -> object:
        nonlocal reads
        reads += 1
        if reads == 1:
            msg = "database busy"
            raise RuntimeError(msg)
        await asyncio.Event().wait()
        return None

    recorder = Mock()
    recorder.async_add_executor_job = hang
    with patch("custom_components.haeo.inputs.meter_history.get_instance", return_value=recorder):
        loader.start()
        await hass.async_block_till_done(wait_background_tasks=False)
        async with asyncio.timeout(1):
            await loader.async_load_all()
            await loader.async_load_all()

    assert store.available
    assert reads == 2
    loader.cleanup()


async def test_an_unloaded_calendar_stops_feeding_its_inputs(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """Events are kept through a failed query, but not once the calendar's entity is gone."""
    calendar = await _add_stub_calendar(hass, [_trip(0.0, 3600.0)])
    store = _calendar_store()
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
    loader.start()
    await hass.async_block_till_done()
    assert store.available

    # Unloading a calendar's integration removes its entity and leaves its state unavailable
    component: EntityComponent[CalendarEntity] = hass.data[CALENDAR_DOMAIN]
    await component.async_remove_entity(calendar.entity_id)
    hass.states.async_set(calendar.entity_id, "unavailable", {"restored": True})
    await loader.async_load_all()

    assert not store.available
    loader.cleanup()


async def test_loader_raises_no_repair_for_unusable_events_past_the_horizon(
    hass: HomeAssistant, horizon_manager: Mock
) -> None:
    """An unusable event fetched ahead of the horizon raises no repair until the horizon reaches it."""
    end = FORECAST_TIMESTAMPS[-1]
    await _add_stub_calendar(hass, [_demand(end + 3600.0, end + 7200.0, "2")])
    store = _forecast_store()
    loader = CalendarInputLoader(hass, "entry_id", {("Load", ("forecast", "forecast")): store}, horizon_manager)
    loader.start()
    await hass.async_block_till_done()

    assert store.available
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ID) is None
    loader.cleanup()


async def test_calendar_change_during_a_refresh_queues_one_more(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """Fetches run one at a time; a change while one runs fetches again once it ends, so it is not missed."""
    calendar = _GatedCalendar()
    await _add_stub_calendars(hass, calendar)
    store = _calendar_store()
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
    started = asyncio.Event()
    started.set()
    calendar.responses.append(([], started))
    loader.start()
    await hass.async_block_till_done()

    slow = asyncio.Event()
    calendar.responses.append(([], slow))
    rerun = asyncio.Event()
    rerun.set()
    calendar.responses.append(([_trip(0.0, 3600.0)], rerun))
    horizon_manager.subscribe.call_args.args[0]()
    await asyncio.sleep(0)
    hass.states.async_set(calendar.entity_id, "on")
    for _ in range(5):
        await asyncio.sleep(0)
    assert len(calendar.responses) == 1

    slow.set()
    await hass.async_block_till_done()

    assert calendar.responses == []
    np.testing.assert_allclose(_presence(store), [1.0, 0.0])
    loader.cleanup()


def _meter_store(timestamps: tuple[float, ...]) -> InputStore:
    """Build a meter input reading METER_ID since its window calendar's open window."""
    sources = {"type": "entity", "value": [METER_ID, ENTITY_ID]}
    return create_input_store(
        value=sources,
        storage=_MemStorage(sources),
        hint=FieldHint(output_type=OutputType.ENERGY, meter=MeterFieldHint(since="window_calendar")),
        get_forecast_timestamps=lambda: timestamps,
    )


async def test_a_roll_during_the_first_meter_read_starts_no_retry(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """The meters' totals are only retried once the first read has finished, so the two never race."""
    start = dt_util.utcnow().timestamp()
    timestamps = (start, start + 3600.0)
    horizon_manager.get_forecast_timestamps.return_value = timestamps
    await _add_stub_calendar(hass, [_demand(start - 3600.0, start + 3600.0, "6 kWh")])
    hass.config.components.add("recorder")
    hass.states.async_set(METER_ID, "12.5", {"unit_of_measurement": "kWh", "device_class": "energy"})
    store = _meter_store(timestamps)
    loader = CalendarInputLoader(hass, "entry_id", {("Pump", ("schedule", "energy_meter")): store}, horizon_manager)
    reads = 0
    answer = asyncio.Event()

    async def slow_then_fail(_func: Callable[..., object], *_args: object) -> object:
        nonlocal reads
        reads += 1
        await answer.wait()
        msg = "database busy"
        raise RuntimeError(msg)

    recorder = Mock()
    recorder.async_add_executor_job = slow_then_fail
    with patch("custom_components.haeo.inputs.meter_history.get_instance", return_value=recorder):
        loader.start()
        await asyncio.sleep(0)
        horizon_manager.subscribe.call_args.args[0]()
        for _ in range(5):
            await asyncio.sleep(0)
        assert reads == 1

        # A retry that fails again leaves the meters on their live readings, and the next load retries
        answer.set()
        await hass.async_block_till_done(wait_background_tasks=True)
        assert reads == 2
        assert store.available

    loader.cleanup()
