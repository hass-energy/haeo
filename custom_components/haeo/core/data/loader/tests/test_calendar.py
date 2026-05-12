"""Tests for calendar event loading and value extraction."""

from datetime import datetime, timezone

from custom_components.haeo.core.data.loader.calendar import (
    CalendarEventData,
    CalendarWindow,
    extract_calendar_windows,
    make_distance_extractor,
    make_presence_extractor,
    parse_distance,
    parse_number,
)


# --- parse_distance ---


def test_parse_distance_km():
    assert parse_distance("50 km") == (50.0, "km")


def test_parse_distance_miles():
    assert parse_distance("30mi") == (30.0, "mi")


def test_parse_distance_decimal():
    assert parse_distance("100.5 kilometers") == (100.5, "km")


def test_parse_distance_metres():
    assert parse_distance("15.2 m") == (15.2, "m")


def test_parse_distance_feet():
    assert parse_distance("500 feet") == (500.0, "ft")


def test_parse_distance_yards():
    assert parse_distance("100 yd") == (100.0, "yd")


def test_parse_distance_unknown_unit():
    assert parse_distance("50 furlongs") is None


def test_parse_distance_no_number():
    assert parse_distance("home") is None


def test_parse_distance_empty():
    assert parse_distance("") is None


def test_parse_distance_whitespace():
    assert parse_distance("  50  km  ") == (50.0, "km")


def test_parse_distance_integer():
    assert parse_distance("100km") == (100.0, "km")


# --- parse_number ---


def test_parse_number_integer():
    assert parse_number("42") == 42.0


def test_parse_number_decimal():
    assert parse_number("3.14") == 3.14


def test_parse_number_whitespace():
    assert parse_number("  7.5  ") == 7.5


def test_parse_number_invalid():
    assert parse_number("abc") is None


def test_parse_number_empty():
    assert parse_number("") is None


# --- extract_calendar_windows ---


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2025, 1, 1, hour, minute, tzinfo=timezone.utc)


def _event(start_h: int, end_h: int, location: str | None = None) -> CalendarEventData:
    return CalendarEventData(start=_dt(start_h), end=_dt(end_h), location=location)


def test_extract_with_presence_extractor():
    events = [_event(9, 10), _event(14, 16)]
    windows = extract_calendar_windows(events, make_presence_extractor())
    assert len(windows) == 2
    assert windows[0].value == 1.0
    assert windows[1].value == 1.0


def test_extract_with_distance_extractor():
    events = [
        CalendarEventData(start=_dt(9), end=_dt(10), location="50 km"),
        CalendarEventData(start=_dt(14), end=_dt(16), location="30 km"),
    ]
    extractor = make_distance_extractor(energy_per_distance=0.2, target_unit="km")
    windows = extract_calendar_windows(events, extractor)
    assert len(windows) == 2
    assert windows[0].value == 10.0  # 50 * 0.2
    assert windows[1].value == 6.0  # 30 * 0.2


def test_extract_skips_no_location():
    events = [CalendarEventData(start=_dt(9), end=_dt(10), location=None)]
    extractor = make_distance_extractor(energy_per_distance=0.2, target_unit="km")
    windows = extract_calendar_windows(events, extractor)
    assert len(windows) == 0


def test_extract_skips_unparseable_location():
    events = [CalendarEventData(start=_dt(9), end=_dt(10), location="home")]
    extractor = make_distance_extractor(energy_per_distance=0.2, target_unit="km")
    windows = extract_calendar_windows(events, extractor)
    assert len(windows) == 0


def test_extract_end_before_start_skipped():
    events = [_event(10, 9)]
    windows = extract_calendar_windows(events, make_presence_extractor())
    assert len(windows) == 0


def test_extract_sorted_by_start():
    events = [_event(14, 16), _event(9, 10)]
    windows = extract_calendar_windows(events, make_presence_extractor())
    assert windows[0].start == _dt(9)
    assert windows[1].start == _dt(14)


def test_extract_unit_conversion():
    events = [CalendarEventData(start=_dt(9), end=_dt(10), location="10 mi")]

    def convert(value: float, from_unit: str, to_unit: str) -> float:
        if from_unit == "mi" and to_unit == "km":
            return value * 1.60934
        return value

    extractor = make_distance_extractor(
        energy_per_distance=0.2, target_unit="km", convert_distance=convert,
    )
    windows = extract_calendar_windows(events, extractor)
    assert len(windows) == 1
    assert abs(windows[0].value - 10 * 1.60934 * 0.2) < 0.001


def test_extract_custom_value_fn():
    """Test with a completely custom extraction function."""
    events = [
        CalendarEventData(start=_dt(9), end=_dt(10), summary="Meeting"),
        CalendarEventData(start=_dt(14), end=_dt(16), summary="3.5 kW"),
    ]

    def extract_power(event: CalendarEventData) -> float | None:
        if event.summary is None:
            return None
        result = parse_number(event.summary.replace(" kW", ""))
        return result

    windows = extract_calendar_windows(events, extract_power)
    assert len(windows) == 1
    assert windows[0].value == 3.5
    assert windows[0].start == _dt(14)


# --- load_calendar_events (diagnostic replay) ---


def test_load_from_captured_events():
    """Load events from pre-captured diagnostics data."""
    from custom_components.haeo.core.data.loader.calendar import load_calendar_events

    value = {
        "type": "calendar",
        "value": "calendar.ev_trips",
        "events": [
            {"start": "2025-01-01T09:00:00+00:00", "end": "2025-01-01T10:00:00+00:00",
             "summary": "Work", "location": "50 km", "description": None},
            {"start": "2025-01-01T17:00:00+00:00", "end": "2025-01-01T18:00:00+00:00",
             "summary": "Home", "location": "50 km", "description": None},
        ],
    }

    events = load_calendar_events(value, _NullSM())
    assert len(events) == 2
    assert events[0].summary == "Work"
    assert events[0].location == "50 km"
    assert events[1].start.hour == 17


def test_load_from_entity_state():
    """Load events from entity state attributes (live path)."""
    from custom_components.haeo.core.data.loader.calendar import load_calendar_events

    value = {"type": "calendar", "value": "calendar.ev", "events": None}
    sm = _MockSM({
        "calendar.ev": _MockState(attributes={
            "haeo_events": [
                {"start": "2025-01-01T09:00:00+00:00", "end": "2025-01-01T10:00:00+00:00",
                 "summary": "Trip", "location": "30 km", "description": None},
            ],
        }),
    })

    events = load_calendar_events(value, sm)
    assert len(events) == 1
    assert events[0].location == "30 km"


def test_load_missing_entity():
    """Return empty list when entity not found."""
    from custom_components.haeo.core.data.loader.calendar import load_calendar_events

    value = {"type": "calendar", "value": "calendar.missing", "events": None}
    events = load_calendar_events(value, _NullSM())
    assert events == []


def test_load_no_haeo_events_attr():
    """Return empty list when entity has no haeo_events attribute."""
    from custom_components.haeo.core.data.loader.calendar import load_calendar_events

    value = {"type": "calendar", "value": "calendar.plain", "events": None}
    sm = _MockSM({"calendar.plain": _MockState(attributes={"friendly_name": "My Cal"})})
    events = load_calendar_events(value, sm)
    assert events == []


# --- capture_calendar_events ---


def test_capture_roundtrip():
    """Capture events and reload them."""
    from custom_components.haeo.core.data.loader.calendar import (
        capture_calendar_events,
        load_calendar_events,
    )

    original = [
        CalendarEventData(start=_dt(9), end=_dt(10), summary="Work", location="50 km"),
        CalendarEventData(start=_dt(17), end=_dt(18), summary="Home", location="50 km"),
    ]

    captured = capture_calendar_events(original)
    assert len(captured) == 2
    assert captured[0]["summary"] == "Work"

    # Reload from captured data
    value = {"type": "calendar", "value": "calendar.ev", "events": captured}
    reloaded = load_calendar_events(value, _NullSM())
    assert len(reloaded) == 2
    assert reloaded[0].summary == "Work"
    assert reloaded[0].location == "50 km"
    assert reloaded[1].start.hour == 17


# --- Test helpers ---


class _MockState:
    def __init__(self, attributes: dict | None = None):
        self.entity_id = "calendar.mock"
        self.state = "on"
        self.attributes = attributes or {}
    def as_dict(self):
        return {"entity_id": self.entity_id, "state": self.state, "attributes": self.attributes}


class _MockSM:
    def __init__(self, states: dict):
        self._states = states
    def get(self, entity_id):
        return self._states.get(entity_id)


class _NullSM:
    def get(self, entity_id):
        return None
