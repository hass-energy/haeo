"""Tests for resolving calendar events into horizon-aligned input series."""

from datetime import UTC, datetime

import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.data.loader.calendar import CALENDAR_EVENTS_ATTRIBUTE
from custom_components.haeo.core.data.loader.calendar_resolver import resolve_calendar
from custom_components.haeo.core.schema.field_hints import CalendarFieldHint, CalendarParser, CalendarProjection

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
    events: list[dict[str, str | None]], projection: CalendarProjection, parser: CalendarParser = "distance"
) -> list[float]:
    sm = FakeStateMachine({ENTITY_ID: FakeEntityState(ENTITY_ID, "on", {CALENDAR_EVENTS_ATTRIBUTE: events})})
    result = resolve_calendar(ENTITY_ID, CalendarFieldHint(parser=parser, projection=projection), sm, BOUNDARY_TIMES)
    assert result is not None
    return result.tolist()


def test_presence_covers_every_event_period() -> None:
    """Presence marks each period an event covers, including events without a value."""
    events = [_event(1, 2, location="50 km"), _event(3, 4, location="Office")]

    assert _resolve(events, "presence") == [0.0, 1.0, 0.0, 1.0]


def test_window_projections_of_one_event() -> None:
    """One event opens a window over its periods, starts at its first boundary, and is due at its end."""
    events = [_event(1, 3, location="50 km")]

    assert _resolve(events, "window_active") == [0.0, 1.0, 1.0, 0.0]
    assert _resolve(events, "window_starts") == [0.0, 1.0, 0.0, 0.0, 0.0]
    assert _resolve(events, "window_due") == [0.0, 0.0, 0.0, 50.0, 0.0]


def test_event_without_a_value_opens_no_window() -> None:
    """An event whose text holds no value marks presence but forms no window."""
    events = [_event(1, 2, location="Office")]

    assert _resolve(events, "window_active") == [0.0, 0.0, 0.0, 0.0]
    assert _resolve(events, "window_due") == [0.0] * 5


def test_overlapping_events_merge_into_one_window() -> None:
    """Overlapping events form one window due at the later end, with their values summed."""
    events = [_event(0, 2, location="10 km"), _event(1, 3, location="20 km")]

    assert _resolve(events, "window_active") == [1.0, 1.0, 1.0, 0.0]
    assert _resolve(events, "window_due") == [0.0, 0.0, 0.0, 30.0, 0.0]


def test_touching_events_stay_separate_windows() -> None:
    """An event starting where another ends starts its own window, and each is due at its own end."""
    events = [_event(0, 2, location="10 km"), _event(2, 3, location="20 km")]

    assert _resolve(events, "window_starts") == [0.0, 0.0, 1.0, 0.0, 0.0]
    assert _resolve(events, "window_due") == [0.0, 0.0, 10.0, 20.0, 0.0]


def test_window_open_at_the_horizon_start_does_not_start() -> None:
    """A window already open in the first period counts as open, not starting."""
    events = [_event(-1, 2, location="10 km")]

    assert _resolve(events, "window_starts") == [0.0] * 5
    assert _resolve(events, "window_due") == [0.0, 0.0, 10.0, 0.0, 0.0]


def test_window_past_the_horizon_is_due_at_its_end() -> None:
    """A window running past the horizon is due at the final boundary."""
    events = [_event(3, 6, location="10 km")]

    assert _resolve(events, "window_due") == [0.0, 0.0, 0.0, 0.0, 10.0]


@pytest.mark.parametrize(
    ("parser", "location", "expected"),
    [
        pytest.param("distance", "10 mi", 16.09344, id="miles_to_km"),
        pytest.param("number", "7.5", 7.5, id="plain_number"),
        pytest.param("presence", None, 1.0, id="presence_ignores_text"),
    ],
)
def test_parsers_value_each_event(parser: CalendarParser, location: str | None, expected: float) -> None:
    """The parser decides each event's value: a distance in km, a plain number, or 1 for any event."""
    due = _resolve([_event(0, 1, location=location)], "window_due", parser)

    assert due[1] == pytest.approx(expected)


def test_calendar_without_events_in_the_horizon_resolves_to_zeros() -> None:
    """A calendar whose injected events are all outside the horizon resolves to zeros."""
    assert _resolve([], "presence") == [0.0] * 4


@pytest.mark.parametrize(
    "states",
    [
        pytest.param({}, id="missing_state"),
        pytest.param({ENTITY_ID: FakeEntityState(ENTITY_ID, "off", {})}, id="no_injected_events"),
    ],
)
def test_calendar_without_injected_events_is_not_loaded(states: dict[str, FakeEntityState]) -> None:
    """A calendar state that is missing or carries no injected events cannot be resolved."""
    hint = CalendarFieldHint(parser="distance", projection="presence")

    assert resolve_calendar(ENTITY_ID, hint, FakeStateMachine(states), BOUNDARY_TIMES) is None
