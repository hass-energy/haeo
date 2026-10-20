"""Calendar event loading — extract time-windowed values from calendar entities.

Calendar entities in HA expose events with start/end times, summary, location,
and description fields. An event's value is a number with its unit, such as
"5 kW", typed in one of its text fields. Events become ``CalendarWindow``
objects that downstream fusers align to the optimization horizon.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, tzinfo
import re
from typing import TYPE_CHECKING, Final, TypedDict

from custom_components.haeo.core.data.util.field_units import to_field_unit

if TYPE_CHECKING:
    from custom_components.haeo.core.model.const import OutputType
    from custom_components.haeo.core.state import EntityState

# State attribute carrying fetched events, injected by the HA-level calendar loader
CALENDAR_EVENTS_ATTRIBUTE: Final = "haeo_events"


class CalendarEventDict(TypedDict):
    """Serialized calendar event, as injected into a calendar state and captured in diagnostics."""

    start: str
    end: str
    summary: str | None
    location: str | None
    description: str | None


@dataclass(frozen=True)
class CalendarWindow:
    """A time window extracted from a calendar event with an associated value."""

    start: datetime
    end: datetime
    value: float


_NUMBER: Final = r"[-+]?(?:\d+(?:\.\d+)?|\.\d+)"

# A number standing as its own word, optionally signed and with decimals,
# then the word typed after it as its unit, if any. A digit inside a word,
# such as in "EV2" or "v1.2", is not a number, nor is the part of a number
# after a comma, slash, colon, or dash, as in "1,500", "1/2", or "10:30".
# A range, such as "8-10 kWh" or "8 to 10 kWh", is one number whose unit is
# the rest of the range, so no input reads it as a value.
# Examples: "50 km", "5kW", "0.30 $/kWh", "-2.5 kW", "3", "EV 8 kWh tonight"
_QUANTITY_PATTERN: Final = re.compile(
    rf"""
    (?<![\w.,/:])(?<!\d[-\u2013])
    (?P<number>{_NUMBER})
    (?P<range>\s*(?:[-\u2013]|\bto\b)\s*{_NUMBER})?
    (?:\s*(?P<unit>[^\s\d.,;:!?()\[\]{{}}"'/+\u2013-][^\s,;:!?()\[\]{{}}"']*))?
    """,
    re.VERBOSE,
)


def find_quantities(text: str) -> list[tuple[float, str | None]]:
    """Return every number in text with the unit typed after it, if any.

    A unit ending a sentence, as in "Charge 8 kWh.", leaves its full stop.
    """
    quantities: list[tuple[float, str | None]] = []
    for match in _QUANTITY_PATTERN.finditer(text):
        unit = text[match.end("number") : match.end()].strip() if match["range"] else match["unit"]
        quantities.append((float(match["number"]), unit.rstrip(".") if unit else None))
    return quantities


@dataclass(frozen=True)
class CalendarEventData:
    """Minimal event data from a calendar entity."""

    start: datetime
    end: datetime
    summary: str | None = None
    location: str | None = None
    description: str | None = None


_TEXT_FIELDS: Final[tuple[str, ...]] = ("location", "summary", "description")


@dataclass(frozen=True)
class EventValueText:
    """The text field an event's value is read from, with the value in an input's unit."""

    field: str
    text: str
    # None when the field holds no number the input can use, or several, so which one is meant is not guessed
    value: float | None


def event_value_text(event: CalendarEventData, output_type: OutputType) -> EventValueText | None:
    """Return the text field an event's value is read from, or None when no field holds a number.

    Fields are tried in order: location, summary, description. The first
    holding any number is the value's field, even when none of its numbers
    can be used, so a later field never silently stands in for a mistyped
    one. The value is the field's one number typed with a unit the input can
    use, so other numbers around it, as in "Tariff 2 at 0.30 $/kWh", are
    passed over. A field holding several such numbers gives no value.
    """
    for field in _TEXT_FIELDS:
        text = getattr(event, field)
        if text and (quantities := find_quantities(text)):
            values = [value for quantity in quantities if (value := to_field_unit(*quantity, output_type)) is not None]
            return EventValueText(field, text, values[0] if len(values) == 1 else None)
    return None


def event_value(event: CalendarEventData, output_type: OutputType) -> float | None:
    """Return an event's value in an input's unit, or None when it has no number or none the input can use."""
    value_text = event_value_text(event, output_type)
    return None if value_text is None else value_text.value


def event_windows(events: Sequence[CalendarEventData], output_type: OutputType) -> list[CalendarWindow]:
    """Return a window per event, sorted by start, holding its value in an input's unit.

    Every event is a window: one without a number, or with one the input
    cannot use, holds zero. Events that end before they start are skipped.
    """
    return sorted(
        (
            CalendarWindow(start=event.start, end=event.end, value=event_value(event, output_type) or 0.0)
            for event in events
            if event.end > event.start
        ),
        key=lambda window: window.start,
    )


def open_window_start(events: Sequence[CalendarEventData], at: datetime) -> float | None:
    """Return the POSIX time the window open at *at* began, or None when no window is open then.

    Windows are formed as for every calendar input: every event is a window,
    overlapping events chain into one, and events that only touch stay
    separate. Calendars are read from the horizon start, so the window begins
    at the earliest start among the events open then.
    """
    windows: list[tuple[datetime, datetime]] = []
    for event in sorted((e for e in events if e.end > e.start), key=lambda e: e.start):
        if windows and event.start < windows[-1][1]:
            windows[-1] = (windows[-1][0], max(windows[-1][1], event.end))
        else:
            windows.append((event.start, event.end))
    return next((start.timestamp() for start, end in windows if start <= at < end), None)


def rejected_events(
    events: Sequence[CalendarEventData], output_type: OutputType
) -> list[tuple[CalendarEventData, EventValueText]]:
    """Return the events holding numbers an input cannot read a value from, with the field it read.

    An event is rejected when its value's field holds no number the input
    can use, or several. A number can be used when its unit converts to the
    input's unit and it is not negative for a quantity that cannot be.
    Inputs ignore these events' values rather than failing, so one mistyped
    event does not stop the rest of the calendar from loading.
    """
    return [
        (event, value_text)
        for event in events
        if (value_text := event_value_text(event, output_type)) is not None and value_text.value is None
    ]


def _normalize_datetime(dt: datetime, time_zone: tzinfo) -> datetime:
    """Attach time_zone to naive datetimes; preserve aware datetimes."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=time_zone)
    return dt


def _optional_str(value: object) -> str | None:
    """Coerce a value to str or None."""
    return value if isinstance(value, str) else None


def load_calendar_events(
    state: EntityState | None,
    time_zone: tzinfo,
) -> list[CalendarEventData] | None:
    """Load the events injected into a calendar entity's state.

    Home Assistant calendar states only show the current or next event, so
    the HA-level calendar loader fetches the horizon's events and injects them
    as the ``haeo_events`` attribute. Captured states keep the attribute, so
    diagnostics and scenarios replay the same events.

    Args:
        state: The calendar entity's state.
        time_zone: Time zone of naive event timestamps, which calendars
            write in local time.

    Returns:
        The events, or None when the state is missing or carries no injected
        events, so the input cannot be resolved.

    """
    if state is None:
        return None
    raw_events = state.attributes.get(CALENDAR_EVENTS_ATTRIBUTE)
    if not isinstance(raw_events, list):
        return None
    return _parse_event_dicts(raw_events, time_zone)


def capture_calendar_events(
    events: list[CalendarEventData],
) -> list[CalendarEventDict]:
    """Serialize calendar events for diagnostics capture.

    Produces the format injected into calendar entity states.
    """
    return [
        CalendarEventDict(
            start=event.start.isoformat(),
            end=event.end.isoformat(),
            summary=event.summary,
            location=event.location,
            description=event.description,
        )
        for event in events
    ]


def _parse_event_dicts(
    raw_events: Sequence[object],
    time_zone: tzinfo,
) -> list[CalendarEventData]:
    """Parse a list of event dicts into CalendarEventData objects."""
    events: list[CalendarEventData] = []
    for raw in raw_events:
        if not isinstance(raw, Mapping):
            continue
        start_str = raw.get("start")
        end_str = raw.get("end")
        if not isinstance(start_str, str) or not isinstance(end_str, str):
            continue
        try:
            start = _normalize_datetime(datetime.fromisoformat(start_str), time_zone)
            end = _normalize_datetime(datetime.fromisoformat(end_str), time_zone)
        except (ValueError, TypeError):
            continue
        events.append(
            CalendarEventData(
                start=start,
                end=end,
                summary=_optional_str(raw.get("summary")),
                location=_optional_str(raw.get("location")),
                description=_optional_str(raw.get("description")),
            )
        )
    return events
