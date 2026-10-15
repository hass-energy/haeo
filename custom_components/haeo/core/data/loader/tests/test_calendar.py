"""Tests for calendar event loading and value extraction."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.data.loader.calendar import (
    CALENDAR_EVENTS_ATTRIBUTE,
    CalendarEventData,
    CalendarEventDict,
    capture_calendar_events,
    event_quantity,
    extract_calendar_windows,
    load_calendar_events,
    parse_quantity,
)
from custom_components.haeo.core.data.util.calendar_fuser import (
    fuse_window_edges_to_boundaries,
    fuse_windows_to_boundaries,
)

# --- parse_quantity ---


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("50 km", (50.0, "km"), id="number_and_unit"),
        pytest.param("5kW", (5.0, "kW"), id="no_space"),
        pytest.param("  0.30 $/kWh  ", (0.30, "$/kWh"), id="price_with_whitespace"),
        pytest.param("-2.5 kW", (-2.5, "kW"), id="negative"),
        pytest.param("42", (42.0, None), id="bare_number"),
        pytest.param("Office", None, id="no_number"),
        pytest.param("", None, id="empty"),
    ],
)
def test_parse_quantity(text: str, expected: tuple[float, str | None] | None) -> None:
    """A number parses with the unit typed after it, if any."""
    assert parse_quantity(text) == expected


# --- event_quantity ---


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2025, 1, 1, hour, minute, tzinfo=UTC)


def _event(start_h: int, end_h: int, location: str | None = None) -> CalendarEventData:
    return CalendarEventData(start=_dt(start_h), end=_dt(end_h), location=location)


@pytest.mark.parametrize(
    ("event", "expected"),
    [
        pytest.param(CalendarEventData(start=_dt(9), end=_dt(10), location="50 km"), (50.0, "km"), id="location"),
        pytest.param(
            CalendarEventData(start=_dt(9), end=_dt(10), location="Office", summary="50 km"),
            (50.0, "km"),
            id="summary_after_unparseable_location",
        ),
        pytest.param(
            CalendarEventData(start=_dt(9), end=_dt(10), location="Office", summary="Commute", description="2 kW"),
            (2.0, "kW"),
            id="description_last",
        ),
        pytest.param(
            CalendarEventData(start=_dt(9), end=_dt(10), location="Office", summary="Commute"),
            None,
            id="no_field_parses",
        ),
        pytest.param(CalendarEventData(start=_dt(9), end=_dt(10)), None, id="no_fields"),
    ],
)
def test_event_quantity_uses_first_field_holding_a_number(
    event: CalendarEventData, expected: tuple[float, str | None] | None
) -> None:
    """The first of location, summary, and description holding a number gives the event's quantity."""
    assert event_quantity(event) == expected


# --- extract_calendar_windows ---


def test_extract_values_each_event() -> None:
    """Each event becomes a window holding the value the function gives it."""
    events = [_event(9, 10), _event(14, 16)]
    windows = extract_calendar_windows(events, lambda _event: 1.0)
    assert [w.value for w in windows] == [1.0, 1.0]


def test_extract_skips_events_without_a_value() -> None:
    """An event the function gives no value is skipped."""
    events = [_event(9, 10, location="Office"), _event(14, 16, location="3 kW")]
    windows = extract_calendar_windows(events, lambda event: q[0] if (q := event_quantity(event)) else None)
    assert len(windows) == 1
    assert windows[0].value == 3.0
    assert windows[0].start == _dt(14)


def test_extract_end_before_start_skipped() -> None:
    """Extract end before start skipped."""
    windows = extract_calendar_windows([_event(10, 9)], lambda _event: 1.0)
    assert len(windows) == 0


def test_extract_sorted_by_start() -> None:
    """Extract sorted by start."""
    windows = extract_calendar_windows([_event(14, 16), _event(9, 10)], lambda _event: 1.0)
    assert windows[0].start == _dt(9)
    assert windows[1].start == _dt(14)


# --- load_calendar_events ---


def _calendar_state(events: list[dict[str, object]] | list[CalendarEventDict]) -> FakeEntityState:
    """Return a calendar state carrying injected events."""
    return FakeEntityState(entity_id="calendar.ev", state="on", attributes={CALENDAR_EVENTS_ATTRIBUTE: events})


def test_load_from_captured_events() -> None:
    """Load events from pre-captured diagnostics data."""
    state = _calendar_state(
        [
            {
                "start": "2025-01-01T09:00:00+00:00",
                "end": "2025-01-01T10:00:00+00:00",
                "summary": "Work",
                "location": "50 km",
                "description": None,
            },
            {
                "start": "2025-01-01T17:00:00+00:00",
                "end": "2025-01-01T18:00:00+00:00",
                "summary": "Home",
                "location": "50 km",
                "description": None,
            },
        ]
    )

    events = load_calendar_events(state)
    assert events is not None
    assert len(events) == 2
    assert events[0].summary == "Work"
    assert events[0].location == "50 km"
    assert events[1].start.hour == 17


def test_load_from_entity_state() -> None:
    """Load events from entity state attributes (live path)."""
    sm = FakeStateMachine(
        {
            "calendar.ev": FakeEntityState(
                entity_id="calendar.ev",
                state="on",
                attributes={
                    "haeo_events": [
                        {
                            "start": "2025-01-01T09:00:00+00:00",
                            "end": "2025-01-01T10:00:00+00:00",
                            "summary": "Trip",
                            "location": "30 km",
                            "description": None,
                        },
                    ],
                },
            ),
        }
    )

    events = load_calendar_events(sm.get("calendar.ev"))
    assert events is not None
    assert len(events) == 1
    assert events[0].location == "30 km"


def test_load_missing_entity() -> None:
    """A missing calendar state has no events to load."""
    assert load_calendar_events(None) is None


def test_load_no_haeo_events_attr() -> None:
    """A calendar state without injected events cannot be resolved."""
    sm = FakeStateMachine(
        {
            "calendar.plain": FakeEntityState(
                entity_id="calendar.plain",
                state="on",
                attributes={"friendly_name": "My Cal"},
            ),
        }
    )
    assert load_calendar_events(sm.get("calendar.plain")) is None


# --- capture_calendar_events ---


def test_capture_roundtrip() -> None:
    """Capture events and reload them."""
    original = [
        CalendarEventData(start=_dt(9), end=_dt(10), summary="Work", location="50 km"),
        CalendarEventData(start=_dt(17), end=_dt(18), summary="Home", location="50 km"),
    ]

    captured = capture_calendar_events(original)
    assert len(captured) == 2
    assert captured[0]["summary"] == "Work"

    # Reload from captured data
    reloaded = load_calendar_events(_calendar_state(captured))
    assert reloaded is not None
    assert len(reloaded) == 2
    assert reloaded[0].summary == "Work"
    assert reloaded[0].location == "50 km"
    assert reloaded[1].start.hour == 17


def test_load_naive_datetime_gets_default_tz() -> None:
    """Naive ISO timestamps are normalized to the supplied default timezone."""
    sydney = ZoneInfo("Australia/Sydney")
    state = _calendar_state(
        [
            {
                "start": "2025-01-01T09:00:00",
                "end": "2025-01-01T10:00:00",
                "summary": "Trip",
                "location": None,
                "description": None,
            },
        ]
    )

    events = load_calendar_events(state, default_tz=sydney)
    assert events is not None
    assert len(events) == 1
    assert events[0].start.tzinfo == sydney
    assert events[0].end.tzinfo == sydney


def test_load_offset_aware_datetime_preserved() -> None:
    """Offset-aware timestamps keep their original timezone."""
    state = _calendar_state(
        [
            {
                "start": "2025-01-01T09:00:00+00:00",
                "end": "2025-01-01T10:00:00+00:00",
                "summary": "Trip",
                "location": None,
                "description": None,
            },
        ]
    )

    events = load_calendar_events(state, default_tz=ZoneInfo("Australia/Sydney"))
    assert events is not None
    assert events[0].start.tzinfo == UTC


def test_naive_and_aware_datetimes_fuse_without_error() -> None:
    """Mixed naive/aware inputs no longer break horizon fusion after normalization."""
    sydney = ZoneInfo("Australia/Sydney")
    state = _calendar_state(
        [
            {
                "start": "2025-01-01T09:00:00",
                "end": "2025-01-01T10:00:00",
                "summary": None,
                "location": "50 km",
                "description": None,
            },
        ]
    )
    events = load_calendar_events(state, default_tz=sydney)
    assert events is not None
    windows = extract_calendar_windows(events, lambda event: q[0] if (q := event_quantity(event)) else None)
    boundaries = [datetime(2025, 1, 1, h, tzinfo=sydney) for h in (8, 9, 10, 11)]

    active = fuse_windows_to_boundaries(windows, boundaries)
    starts = fuse_window_edges_to_boundaries(windows, boundaries, edge="start")
    ends = fuse_window_edges_to_boundaries(windows, boundaries, edge="end")

    assert active == [None, 50.0, None, None]
    assert starts == [None, 50.0, None, None]
    assert ends == [None, None, 50.0, None]


def test_load_skips_invalid_event_dicts() -> None:
    """Skip events with invalid or missing start/end fields."""
    state = _calendar_state(
        [
            {
                "start": "not-a-date",
                "end": "2025-01-01T10:00:00+00:00",
                "summary": None,
                "location": None,
                "description": None,
            },
            {
                "start": "2025-01-01T09:00:00+00:00",
                "end": "also-bad",
                "summary": None,
                "location": None,
                "description": None,
            },
            {"summary": "no dates", "location": None, "description": None},
            42,  # type: ignore[list-item]  # not a mapping
            {
                "start": "2025-01-01T09:00:00+00:00",
                "end": "2025-01-01T10:00:00+00:00",
                "summary": "Valid",
                "location": None,
                "description": None,
            },
        ]
    )
    events = load_calendar_events(state)
    assert events is not None
    assert len(events) == 1
    assert events[0].summary == "Valid"
