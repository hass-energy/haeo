"""Tests for the calendar input loader and event-injecting state machine."""

import asyncio
from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime
import logging
from unittest.mock import Mock

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.components.calendar.const import DOMAIN as CALENDAR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.util import dt as dt_util
import numpy as np
import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.calendar_loader import CalendarInputLoader, CalendarStateMachine
from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.data.input_store import InputStore, create_input_store
from custom_components.haeo.core.data.loader.calendar import CALENDAR_EVENTS_ATTRIBUTE, CalendarEventDict
from custom_components.haeo.core.data.loader.meter import METER_TOTALS_ATTRIBUTE
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.field_hints import FieldHint, MeterFieldHint, calendar_input
from custom_components.haeo.horizon import HorizonManager

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


# --- CalendarStateMachine ---


def test_state_machine_injects_events_for_known_calendars() -> None:
    """Known calendar entities get events merged into their attributes."""
    base = FakeStateMachine({ENTITY_ID: FakeEntityState(ENTITY_ID, "on", {"existing": 1})})
    events = [
        CalendarEventDict(
            start="2026-01-01T00:00:00+00:00",
            end="2026-01-01T01:00:00+00:00",
            summary="Trip",
            location=None,
            description=None,
        )
    ]
    sm = CalendarStateMachine(base, {ENTITY_ID: events})

    state = sm.get(ENTITY_ID)

    assert state is not None
    assert state.entity_id == ENTITY_ID
    assert state.state == "on"
    assert state.attributes["existing"] == 1
    assert state.attributes[CALENDAR_EVENTS_ATTRIBUTE] == events
    serialized_attributes = state.as_dict()["attributes"]
    assert isinstance(serialized_attributes, Mapping)
    assert serialized_attributes[CALENDAR_EVENTS_ATTRIBUTE] == events


def test_state_machine_passes_through_other_entities() -> None:
    """Entities without event lists are returned unmodified."""
    base = FakeStateMachine({"sensor.x": FakeEntityState("sensor.x", "1.0", {})})
    sm = CalendarStateMachine(base, {})

    state = sm.get("sensor.x")

    assert state is not None
    assert CALENDAR_EVENTS_ATTRIBUTE not in state.attributes
    assert sm.get("sensor.missing") is None


def test_state_machine_reads_a_calendar_without_events_as_missing() -> None:
    """A calendar whose events were not fetched reads as missing, not as its plain state."""
    base = FakeStateMachine({ENTITY_ID: FakeEntityState(ENTITY_ID, "off", {})})
    sm = CalendarStateMachine(base, {ENTITY_ID: None})

    assert sm.get(ENTITY_ID) is None


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


async def test_loader_failed_reload_makes_store_unavailable_and_notifies(
    hass: HomeAssistant, horizon_manager: Mock
) -> None:
    """A failed event fetch makes the store unavailable and tells its listeners, so optimization stops."""
    calendar = await _add_stub_calendar(hass, [_trip(0.0, 3600.0)])
    store = _calendar_store()
    listener = Mock()
    store.add_listener(listener)
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
    loader.start()
    await hass.async_block_till_done()
    listener.reset_mock()

    calendar.fail = True
    await loader.async_load_all()
    await loader.async_load_all()

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
    await loader.async_resolve()

    assert store.available
    listener.assert_not_called()
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


async def test_loader_skips_events_fetched_for_a_previous_horizon(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """A fetch that finishes after the horizon moved leaves the store for the reload the move scheduled."""
    calendar = _GatedCalendar()
    await _add_stub_calendars(hass, calendar)
    store = _calendar_store()
    loader = CalendarInputLoader(hass, "entry_id", {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
    gate = asyncio.Event()
    calendar.responses.append(([_trip(0.0, 3600.0)], gate))

    loader.start()
    await asyncio.sleep(0)
    horizon_manager.get_forecast_timestamps.return_value = (3600.0, 7200.0, 10800.0)
    gate.set()
    await hass.async_block_till_done()

    assert not store.is_ready()
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
