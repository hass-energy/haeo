"""Tests for calendar event loading and value extraction."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.data.loader.calendar import (
    CALENDAR_EVENTS_ATTRIBUTE,
    CalendarEventData,
    CalendarEventDict,
    EventValueText,
    capture_calendar_events,
    event_value_text,
    event_windows,
    find_quantities,
    load_calendar_events,
    open_window_start,
    rejected_events,
)
from custom_components.haeo.core.data.util.calendar_fuser import (
    fuse_window_edges_to_boundaries,
    fuse_windows_to_boundaries,
)
from custom_components.haeo.core.model.const import OutputType

# --- find_quantities ---


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("50 km", [(50.0, "km")], id="number_and_unit"),
        pytest.param("5kW", [(5.0, "kW")], id="no_space"),
        pytest.param("  0.30 $/kWh  ", [(0.30, "$/kWh")], id="price_with_whitespace"),
        pytest.param("-2.5 kW", [(-2.5, "kW")], id="negative"),
        pytest.param(".5 kWh", [(0.5, "kWh")], id="leading_decimal_point"),
        pytest.param("42", [(42.0, None)], id="bare_number"),
        pytest.param("EV 8 kWh", [(8.0, "kWh")], id="word_before"),
        pytest.param("Charge 8kWh tonight", [(8.0, "kWh")], id="words_around"),
        pytest.param("Charge 8 kWh.", [(8.0, "kWh")], id="full_stop_after_unit"),
        pytest.param("Charge 8 kWh, then rest", [(8.0, "kWh")], id="comma_after_unit"),
        pytest.param("Peak (0.30 $/kWh)", [(0.30, "$/kWh")], id="in_parentheses"),
        pytest.param("Charge 5 by noon", [(5.0, "by")], id="word_after_is_the_unit"),
        pytest.param("EV2 8 kWh", [(8.0, "kWh")], id="digit_inside_word_is_not_a_number"),
        pytest.param("Firmware v1.2", [], id="version_is_not_a_number"),
        pytest.param("8 kWh or 10 kWh", [(8.0, "kWh"), (10.0, "kWh")], id="several"),
        pytest.param("Tariff 2 at 0.30 $/kWh", [(2.0, "at"), (0.30, "$/kWh")], id="number_before_value"),
        pytest.param("8-10 kWh", [(8.0, "-10 kWh")], id="range"),
        pytest.param("8 - 10 kWh", [(8.0, "- 10 kWh")], id="spaced_range"),
        pytest.param("8  to  10 kWh", [(8.0, "to  10 kWh")], id="worded_range"),
        pytest.param("2026-10-22", [(2026.0, "-10")], id="date"),
        pytest.param("1,500 Wh", [(1.0, None)], id="thousands_separator"),
        pytest.param("1/2 kWh", [(1.0, None)], id="fraction"),
        pytest.param("At 10:30", [(10.0, None)], id="time"),
        pytest.param("Office", [], id="no_number"),
        pytest.param("", [], id="empty"),
    ],
)
def test_find_quantities(text: str, expected: list[tuple[float, str | None]]) -> None:
    """Every number standing as its own word is found, with the word typed after it as its unit."""
    assert find_quantities(text) == expected


# --- event_value_text ---


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2025, 1, 1, hour, minute, tzinfo=UTC)


def _event(start_h: int, end_h: int, location: str | None = None) -> CalendarEventData:
    return CalendarEventData(start=_dt(start_h), end=_dt(end_h), location=location)


def _text_event(
    location: str | None = None, summary: str | None = None, description: str | None = None
) -> CalendarEventData:
    return CalendarEventData(start=_dt(9), end=_dt(10), location=location, summary=summary, description=description)


@pytest.mark.parametrize(
    ("event", "output_type", "expected"),
    [
        pytest.param(
            _text_event(location="5 kW"), OutputType.POWER, EventValueText("location", "5 kW", 5.0), id="location"
        ),
        pytest.param(
            _text_event(location="Office", summary="EV 8 kWh"),
            OutputType.ENERGY,
            EventValueText("summary", "EV 8 kWh", 8.0),
            id="summary_after_location_without_number",
        ),
        pytest.param(
            _text_event(location="Office", summary="Commute", description="2000 W"),
            OutputType.POWER,
            EventValueText("description", "2000 W", 2.0),
            id="description_last_converted",
        ),
        pytest.param(
            _text_event(summary="Tariff 2 at 0.30 $/kWh"),
            OutputType.PRICE,
            EventValueText("summary", "Tariff 2 at 0.30 $/kWh", 0.30),
            id="other_numbers_passed_over",
        ),
        pytest.param(
            _text_event(summary="Charger 7 kW, needs 8 kWh"),
            OutputType.ENERGY,
            EventValueText("summary", "Charger 7 kW, needs 8 kWh", 8.0),
            id="number_in_another_quantity_passed_over",
        ),
        pytest.param(
            _text_event(location="12 Main St", summary="Trip 40 km"),
            OutputType.DISTANCE,
            EventValueText("summary", "Trip 40 km", 40.0),
            id="street_number_in_location_passed_over",
        ),
        pytest.param(
            _text_event(location="40 km", summary="Visit 3 friends"),
            OutputType.DISTANCE,
            EventValueText("location", "40 km", 40.0),
            id="usable_location_before_summary",
        ),
        pytest.param(
            _text_event(location="8", description="2 kWh"),
            OutputType.ENERGY,
            EventValueText("description", "2 kWh", 2.0),
            id="field_without_a_usable_number_passed_over",
        ),
        pytest.param(
            _text_event(location="12 Main St", summary="EV 8"),
            OutputType.ENERGY,
            EventValueText("location", "12 Main St", None),
            id="first_field_with_a_number_when_none_is_usable",
        ),
        pytest.param(
            _text_event(location="12 Main St", summary="8 kWh or 10 kWh"),
            OutputType.ENERGY,
            EventValueText("summary", "8 kWh or 10 kWh", None),
            id="several_usable_numbers_after_an_unusable_field_give_no_value",
        ),
        pytest.param(
            _text_event(summary="8 kWh or 10 kWh", description="8 kWh"),
            OutputType.ENERGY,
            EventValueText("summary", "8 kWh or 10 kWh", None),
            id="several_usable_numbers_give_no_value",
        ),
        pytest.param(
            _text_event(location="Bay 3"),
            OutputType.AVAILABILITY,
            EventValueText("location", "Bay 3", 3.0),
            id="bare_number_for_unitless_input",
        ),
        pytest.param(_text_event(location="Office", summary="Commute"), OutputType.ENERGY, None, id="no_number"),
        pytest.param(_text_event(), OutputType.ENERGY, None, id="no_fields"),
    ],
)
def test_event_value_text_is_the_first_field_holding_a_usable_number(
    event: CalendarEventData, output_type: OutputType, expected: EventValueText | None
) -> None:
    """The first of location, summary, and description holding a usable number gives the value.

    With no usable number in any field, the first field holding a number is the one reported.
    """
    assert event_value_text(event, output_type) == expected


@pytest.mark.parametrize(
    ("summary", "output_type", "rejected"),
    [
        pytest.param("EV 8 kWh", OutputType.ENERGY, False, id="number_and_unit"),
        pytest.param("Tariff 2 at 0.30 $/kWh", OutputType.PRICE, False, id="other_numbers_around"),
        pytest.param("Pool pump", OutputType.ENERGY, False, id="no_number"),
        pytest.param("EV 8", OutputType.ENERGY, True, id="no_unit"),
        pytest.param("Charge 8 by noon", OutputType.ENERGY, True, id="unknown_unit"),
        pytest.param("EV 8 kW", OutputType.ENERGY, True, id="unit_of_another_quantity"),
        pytest.param("EV -8 kWh", OutputType.ENERGY, True, id="negative"),
        pytest.param("EV 8 kWh then 2 kWh", OutputType.ENERGY, True, id="several_usable_numbers"),
        pytest.param("8-10 kWh", OutputType.ENERGY, True, id="range"),
        pytest.param("8 to 10 kWh", OutputType.ENERGY, True, id="worded_range"),
        pytest.param("Peak 30c/kWh", OutputType.PRICE, False, id="cents_price"),
        pytest.param("1,500 Wh", OutputType.ENERGY, True, id="thousands_separator"),
        pytest.param("Rebate -0.10 $/kWh", OutputType.PRICE, False, id="negative_price"),
    ],
)
def test_rejected_events_hold_numbers_the_input_cannot_read_a_value_from(
    summary: str, output_type: OutputType, rejected: bool
) -> None:
    """An event holding numbers but no single value the input can use is rejected with its text."""
    event = _text_event(summary=summary)

    result = rejected_events([event], output_type)

    assert [(rejected_event, value_text.text) for rejected_event, value_text in result] == (
        [(event, summary)] if rejected else []
    )


# --- event_windows ---


def test_every_event_is_a_window_holding_its_value() -> None:
    """Each event becomes a window holding its value in the input's unit, or zero when it has none it can use."""
    events = [_event(9, 10, location="Office"), _event(11, 12, location="3"), _event(14, 16, location="3000 W")]

    windows = event_windows(events, OutputType.POWER)

    assert [w.value for w in windows] == [0.0, 0.0, 3.0]


def test_event_windows_skip_events_ending_before_they_start() -> None:
    """An event that ends before it starts is not a window."""
    assert event_windows([_event(10, 9, location="1 kW")], OutputType.POWER) == []


def test_event_windows_sorted_by_start() -> None:
    """Windows are sorted by start."""
    windows = event_windows([_event(14, 16), _event(9, 10)], OutputType.POWER)

    assert [w.start for w in windows] == [_dt(9), _dt(14)]


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

    events = load_calendar_events(state, UTC)
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

    events = load_calendar_events(sm.get("calendar.ev"), UTC)
    assert events is not None
    assert len(events) == 1
    assert events[0].location == "30 km"


def test_load_missing_entity() -> None:
    """A missing calendar state has no events to load."""
    assert load_calendar_events(None, UTC) is None


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
    assert load_calendar_events(sm.get("calendar.plain"), UTC) is None


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
    reloaded = load_calendar_events(_calendar_state(captured), UTC)
    assert reloaded is not None
    assert len(reloaded) == 2
    assert reloaded[0].summary == "Work"
    assert reloaded[0].location == "50 km"
    assert reloaded[1].start.hour == 17


def test_load_naive_datetime_reads_local_time() -> None:
    """Naive ISO timestamps are read in the supplied local time zone, including half-hour offsets."""
    adelaide = ZoneInfo("Australia/Adelaide")
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

    events = load_calendar_events(state, adelaide)
    assert events is not None
    assert len(events) == 1
    # Adelaide is UTC+10:30 in January
    assert events[0].start == datetime(2024, 12, 31, 22, 30, tzinfo=UTC)
    assert events[0].end == datetime(2024, 12, 31, 23, 30, tzinfo=UTC)


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

    events = load_calendar_events(state, ZoneInfo("Australia/Sydney"))
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
                "location": "50 kWh",
                "description": None,
            },
        ]
    )
    events = load_calendar_events(state, sydney)
    assert events is not None
    windows = event_windows(events, OutputType.ENERGY)
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
    events = load_calendar_events(state, UTC)
    assert events is not None
    assert len(events) == 1
    assert events[0].summary == "Valid"


# --- open_window_start ---


@pytest.mark.parametrize(
    ("spans", "expected_hour"),
    [
        pytest.param([(8, 11)], 8, id="open_event"),
        pytest.param([(7, 10), (8, 11)], 7, id="earliest_open_event"),
        pytest.param([(7, 9), (8, 11)], 8, id="events_ended_before_are_not_in_the_window"),
        pytest.param([(7, 9), (9, 11)], 9, id="touching_events_stay_separate"),
        pytest.param([(11, 12)], None, id="none_open"),
        pytest.param([(10, 9)], None, id="ends_before_it_starts"),
    ],
)
def test_open_window_start(spans: list[tuple[int, int]], expected_hour: int | None) -> None:
    """The window open at a time began at the earliest of the events open then; ended events are not part of it."""
    events = [_event(start, end) for start, end in spans]

    opened = open_window_start(events, _dt(9, 30))

    assert opened == (None if expected_hour is None else _dt(expected_hour).timestamp())
