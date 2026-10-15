"""Tests for the calendar input loader and event-injecting state machine."""

import asyncio
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
import logging
from unittest.mock import Mock

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.components.calendar.const import DOMAIN as CALENDAR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_component import EntityComponent
import numpy as np
import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.calendar_loader import CalendarInputLoader, CalendarStateMachine
from custom_components.haeo.core.data.input_store import InputStore, create_input_store
from custom_components.haeo.core.data.loader.calendar import CALENDAR_EVENTS_ATTRIBUTE
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.field_hints import FieldHint, calendar_input
from custom_components.haeo.horizon import HorizonManager

_LOGGER = logging.getLogger(__name__)

FORECAST_TIMESTAMPS: tuple[float, ...] = (0.0, 3600.0, 7200.0)

ENTITY_ID = "calendar.trips"


class _MemStorage:
    """In-memory storage double implementing the Storage protocol."""

    def __init__(self, value: object) -> None:
        self.value = value

    def read(self) -> object:
        return self.value

    async def write(self, value: object) -> None:
        self.value = value


def _calendar_store(
    entity_id: str = ENTITY_ID,
    get_forecast_timestamps: Callable[[], tuple[float, ...]] = lambda: FORECAST_TIMESTAMPS,
) -> InputStore:
    """Build a store for a calendar input reading a calendar entity's presence."""
    return create_input_store(
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
        start_date: datetime,  # noqa: ARG002
        end_date: datetime,  # noqa: ARG002
    ) -> list[CalendarEvent]:
        """Return all canned events regardless of range, yielding like a real fetch."""
        await asyncio.sleep(0)
        if self.fail:
            msg = "Calendar backend unreachable"
            raise HomeAssistantError(msg)
        return self._events


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
    events = [{"start": "2026-01-01T00:00:00+00:00", "end": "2026-01-01T01:00:00+00:00"}]
    sm = CalendarStateMachine(base, {ENTITY_ID: events})  # type: ignore[arg-type]  # test uses plain dicts

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
    loader = CalendarInputLoader(hass, {("EV", ("trip", "trip_calendar")): store}, horizon_manager)

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
    loader = CalendarInputLoader(hass, {("EV", ("trip", "trip_calendar")): store}, horizon_manager)

    loader.start()
    await hass.async_block_till_done()

    assert not store.available
    loader.cleanup()


async def test_loader_reloads_on_calendar_state_change(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """A calendar entity state change triggers a reload."""
    await _add_stub_calendar(hass, [])
    store = _calendar_store()
    loader = CalendarInputLoader(hass, {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
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
    loader = CalendarInputLoader(hass, {}, horizon_manager)

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
    loader = CalendarInputLoader(hass, {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
    loader.start()
    await hass.async_block_till_done()
    listener.reset_mock()

    calendar.fail = True
    await loader.async_load_all()
    await loader.async_load_all()

    assert not store.available
    listener.assert_called_once()
    loader.cleanup()


async def test_loader_initial_fetch_failure_leaves_store_not_ready(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """A failed first fetch does not load the store as an empty calendar."""
    calendar = await _add_stub_calendar(hass, [_trip(0.0, 3600.0)])
    calendar.fail = True
    store = _calendar_store()
    loader = CalendarInputLoader(hass, {("EV", ("trip", "trip_calendar")): store}, horizon_manager)

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
    loader = CalendarInputLoader(hass, {("EV", ("trip", "trip_presence")): store}, horizon_manager)

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
    loader = CalendarInputLoader(hass, {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
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
        start_date: datetime,  # noqa: ARG002
        end_date: datetime,  # noqa: ARG002
    ) -> list[CalendarEvent]:
        """Return the next queued events after waiting for that fetch's gate."""
        events, gate = self.responses.pop(0)
        await gate.wait()
        return events


async def test_loader_applies_overlapping_reloads_in_trigger_order(hass: HomeAssistant, horizon_manager: Mock) -> None:
    """An older reload finishing after a newer one does not overwrite the store with stale events."""
    calendar = _GatedCalendar()
    await _add_stub_calendars(hass, calendar)
    store = _calendar_store()
    loader = CalendarInputLoader(hass, {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
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
    loader = CalendarInputLoader(hass, {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
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
    loader = CalendarInputLoader(hass, {("EV", ("trip", "trip_calendar")): store}, horizon_manager)
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
        storage=_MemStorage({"type": "entity", "value": ["sensor.base", ENTITY_ID]}),
        hint=FieldHint(output_type=OutputType.POWER, time_series=True),
        get_forecast_timestamps=lambda: timestamps,
    )
    loader = CalendarInputLoader(hass, {("Load", ("forecast", "forecast")): store}, horizon_manager)
    loader.start()
    await hass.async_block_till_done()
    np.testing.assert_allclose(_presence(store), [1.0, 2.0])

    calendar.fail = True
    _set_base(5.0)
    await hass.async_block_till_done()

    np.testing.assert_allclose(_presence(store), [5.0, 2.0])
    loader.cleanup()
