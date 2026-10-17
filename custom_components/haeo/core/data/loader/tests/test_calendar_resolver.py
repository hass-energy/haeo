"""Tests for resolving calendar events into horizon-aligned input series."""

from datetime import UTC, datetime

import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.data.loader.calendar import CALENDAR_EVENTS_ATTRIBUTE
from custom_components.haeo.core.data.loader.calendar_resolver import resolve_calendar
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.field_hints import CalendarFieldHint, CalendarProjection

# Hourly boundaries: 5 boundaries defining 4 periods, starting at epoch 0 (UTC).
BOUNDARY_TIMES: tuple[float, ...] = (0.0, 3600.0, 7200.0, 10800.0, 14400.0)

ENTITY_ID = "calendar.trips"


def _event(start_h: float, end_h: float, location: str | None = None) -> dict[str, str | None]:
    """Build an injected event dict spanning the given hours after epoch 0."""
    return {
        "start": datetime.fromtimestamp(start_h * 3600.0, tz=UTC).isoformat(),
        "end": datetime.fromtimestamp(end_h * 3600.0, tz=UTC).isoformat(),
        "summary": "Trip",
        "location": location,
        "description": None,
    }


def _resolve(
    events: list[dict[str, str | None]], projection: CalendarProjection, output_type: OutputType = OutputType.ENERGY
) -> list[float]:
    sm = FakeStateMachine({ENTITY_ID: FakeEntityState(ENTITY_ID, "on", {CALENDAR_EVENTS_ATTRIBUTE: events})})
    result = resolve_calendar([ENTITY_ID], CalendarFieldHint(projection=projection), output_type, sm, BOUNDARY_TIMES)
    assert result is not None
    return result.tolist()


def test_every_event_is_a_window() -> None:
    """Each event's periods are in a window, including an event without a value."""
    events = [_event(1, 2, location="50 kWh"), _event(3, 4, location="Office")]

    assert _resolve(events, "window_active") == [0.0, 1.0, 0.0, 1.0]


def test_window_projections_of_one_event() -> None:
    """One event opens a window over its periods, starts at its first boundary, and is due at its end."""
    events = [_event(1, 3, location="50 kWh")]

    assert _resolve(events, "window_active") == [0.0, 1.0, 1.0, 0.0]
    assert _resolve(events, "window_starts") == [0.0, 1.0, 0.0, 0.0, 0.0]
    assert _resolve(events, "window_due") == [0.0, 0.0, 0.0, 50.0, 0.0]


def test_event_without_a_value_is_a_window_due_nothing() -> None:
    """An event whose text holds no value is still a window, such as time away without a trip."""
    events = [_event(1, 2, location="Office")]

    assert _resolve(events, "window_active") == [0.0, 1.0, 0.0, 0.0]
    assert _resolve(events, "window_starts") == [0.0, 1.0, 0.0, 0.0, 0.0]
    assert _resolve(events, "window_due") == [0.0] * 5


def test_touching_events_without_values_stay_separate_windows() -> None:
    """Touching events stay separate windows whether or not they hold values."""
    events = [_event(0, 1, location="Office"), _event(1, 3, location="20 kWh")]

    assert _resolve(events, "window_starts") == [0.0, 1.0, 0.0, 0.0, 0.0]
    assert _resolve(events, "window_due") == [0.0, 0.0, 0.0, 20.0, 0.0]


def test_overlapping_events_merge_into_one_window() -> None:
    """Overlapping events form one window due at the later end, with their values summed."""
    events = [_event(0, 2, location="10 kWh"), _event(1, 3, location="20 kWh")]

    assert _resolve(events, "window_active") == [1.0, 1.0, 1.0, 0.0]
    assert _resolve(events, "window_due") == [0.0, 0.0, 0.0, 30.0, 0.0]


def test_touching_events_stay_separate_windows() -> None:
    """An event starting where another ends starts its own window, and each is due at its own end."""
    events = [_event(0, 2, location="10 kWh"), _event(2, 3, location="20 kWh")]

    assert _resolve(events, "window_starts") == [0.0, 0.0, 1.0, 0.0, 0.0]
    assert _resolve(events, "window_due") == [0.0, 0.0, 10.0, 20.0, 0.0]


def test_window_open_at_the_horizon_start_does_not_start() -> None:
    """A window already open in the first period counts as open, not starting."""
    events = [_event(-1, 2, location="10 kWh")]

    assert _resolve(events, "window_starts") == [0.0] * 5
    assert _resolve(events, "window_due") == [0.0, 0.0, 10.0, 0.0, 0.0]


def test_window_past_the_horizon_is_due_at_its_end() -> None:
    """A window running past the horizon is due at the final boundary."""
    events = [_event(3, 6, location="10 kWh")]

    assert _resolve(events, "window_due") == [0.0, 0.0, 0.0, 0.0, 10.0]


@pytest.mark.parametrize(
    ("location", "output_type", "expected"),
    [
        pytest.param("500 Wh", OutputType.ENERGY, 0.5, id="converts_to_kwh"),
        pytest.param("2 MWh", OutputType.ENERGY, 2000.0, id="converts_from_mwh"),
        pytest.param("3", OutputType.AVAILABILITY, 3.0, id="bare_number_for_unitless_input"),
    ],
)
def test_due_values_convert_to_the_input_unit(location: str, output_type: OutputType, expected: float) -> None:
    """Each event's value converts from the unit typed with it to the input's unit."""
    due = _resolve([_event(0, 1, location=location)], "window_due", output_type)

    assert due[1] == pytest.approx(expected)


@pytest.mark.parametrize(
    ("location", "output_type"),
    [
        pytest.param("50", OutputType.ENERGY, id="bare_number"),
        pytest.param("5 kW", OutputType.ENERGY, id="unit_does_not_convert"),
        pytest.param("3 kWh", OutputType.AVAILABILITY, id="unit_for_unitless_input"),
    ],
)
def test_due_values_the_input_cannot_use_are_ignored(location: str, output_type: OutputType) -> None:
    """An event whose value the input cannot use is still a window, due nothing, beside events that load."""
    events = [
        _event(0, 1, location=location),
        _event(2, 3, location="2 kWh" if output_type == OutputType.ENERGY else "2"),
    ]

    due = _resolve(events, "window_due", output_type)

    assert due == pytest.approx([0.0, 0.0, 0.0, 2.0, 0.0])


def test_windows_ignore_event_values() -> None:
    """Window flags do not read event values, so a value the input could not use does not affect them."""
    assert _resolve([_event(1, 2, location="5 kW")], "window_active") == [0.0, 1.0, 0.0, 0.0]


def test_calendar_without_events_in_the_horizon_resolves_to_zeros() -> None:
    """A calendar whose injected events are all outside the horizon resolves to zeros."""
    assert _resolve([], "window_active") == [0.0] * 4


@pytest.mark.parametrize(
    "states",
    [
        pytest.param({}, id="missing_state"),
        pytest.param({ENTITY_ID: FakeEntityState(ENTITY_ID, "off", {})}, id="no_injected_events"),
    ],
)
def test_calendar_without_injected_events_is_not_loaded(states: dict[str, FakeEntityState]) -> None:
    """A calendar state that is missing or carries no injected events cannot be resolved."""
    hint = CalendarFieldHint(projection="window_active")

    assert (
        resolve_calendar([ENTITY_ID], hint, OutputType.AVAILABILITY, FakeStateMachine(states), BOUNDARY_TIMES) is None
    )


def test_events_of_every_calendar_count_together() -> None:
    """An input reading several calendars resolves their events together, and is not loaded while one is missing."""
    other = "calendar.other"
    states = {
        ENTITY_ID: FakeEntityState(ENTITY_ID, "on", {CALENDAR_EVENTS_ATTRIBUTE: [_event(0, 1, location="1 kWh")]}),
        other: FakeEntityState(other, "on", {CALENDAR_EVENTS_ATTRIBUTE: [_event(2, 3, location="2 kWh")]}),
    }
    hint = CalendarFieldHint(projection="window_due")

    due = resolve_calendar([ENTITY_ID, other], hint, OutputType.ENERGY, FakeStateMachine(states), BOUNDARY_TIMES)

    assert due is not None
    assert due.tolist() == [0.0, 1.0, 0.0, 2.0, 0.0]
    del states[other]
    assert (
        resolve_calendar([ENTITY_ID, other], hint, OutputType.ENERGY, FakeStateMachine(states), BOUNDARY_TIMES) is None
    )
