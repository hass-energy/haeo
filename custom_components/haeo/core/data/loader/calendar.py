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


# A number, optionally signed and with decimals, then an optional unit
# Examples: "50 km", "5kW", "0.30 $/kWh", "-2.5 kW", "3"
_QUANTITY_PATTERN: Final = re.compile(r"^\s*([-+]?\d+(?:\.\d+)?)\s*(\S(?:.*\S)?)?\s*$")


def parse_quantity(text: str) -> tuple[float, str | None] | None:
    """Parse a number with an optional unit from text, or None when the text is not one."""
    match = _QUANTITY_PATTERN.match(text)
    if match is None:
        return None
    return float(match.group(1)), match.group(2)


@dataclass(frozen=True)
class CalendarEventData:
    """Minimal event data from a calendar entity."""

    start: datetime
    end: datetime
    summary: str | None = None
    location: str | None = None
    description: str | None = None


_TEXT_FIELDS: Final[tuple[str, ...]] = ("location", "summary", "description")


def event_quantity(event: CalendarEventData) -> tuple[float, str | None] | None:
    """Return the number and unit of the first text field holding one, or None when no field does.

    Fields are tried in order: location, summary, description.
    """
    for field in _TEXT_FIELDS:
        text = getattr(event, field)
        if text and (quantity := parse_quantity(text)) is not None:
            return quantity
    return None


def event_value(event: CalendarEventData, output_type: OutputType) -> float | None:
    """Return an event's value in an input's unit, or None when it has no number or one the input cannot use."""
    quantity = event_quantity(event)
    return None if quantity is None else to_field_unit(*quantity, output_type)


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


def open_since_field(field_name: str) -> str:
    """Return the loaded config key holding when the window open at the horizon start began, for a calendar field."""
    return f"{field_name}_open_since"


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
) -> list[tuple[CalendarEventData, str]]:
    """Return the events holding a number an input cannot use, such as one without a unit, with the value as typed.

    Inputs ignore these events' values rather than failing, so one mistyped
    event does not stop the rest of the calendar from loading.
    """
    return [
        (event, f"{quantity[0]:g}" if quantity[1] is None else f"{quantity[0]:g} {quantity[1]}")
        for event in events
        if (quantity := event_quantity(event)) is not None and to_field_unit(*quantity, output_type) is None
    ]


def _default_local_timezone() -> tzinfo:
    """Return the system local timezone for naive datetime normalization."""
    local_tz = datetime.now().astimezone().tzinfo
    if local_tz is None:
        msg = "System local timezone is unavailable"
        raise RuntimeError(msg)
    return local_tz


def _normalize_datetime(dt: datetime, default_tz: tzinfo) -> datetime:
    """Attach default_tz to naive datetimes; preserve aware datetimes."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=default_tz)
    return dt


def _optional_str(value: object) -> str | None:
    """Coerce a value to str or None."""
    return value if isinstance(value, str) else None


def load_calendar_events(
    state: EntityState | None,
    *,
    default_tz: tzinfo | None = None,
) -> list[CalendarEventData] | None:
    """Load the events injected into a calendar entity's state.

    Home Assistant calendar states only show the current or next event, so
    the HA-level calendar loader fetches the horizon's events and injects them
    as the ``haeo_events`` attribute. Captured states keep the attribute, so
    diagnostics and scenarios replay the same events.

    Args:
        state: The calendar entity's state.
        default_tz: Timezone assumed for naive event timestamps. Defaults to
            the system local timezone.

    Returns:
        The events, or None when the state is missing or carries no injected
        events, so the input cannot be resolved.

    """
    if state is None:
        return None
    raw_events = state.attributes.get(CALENDAR_EVENTS_ATTRIBUTE)
    if not isinstance(raw_events, list):
        return None
    tz = default_tz if default_tz is not None else _default_local_timezone()
    return _parse_event_dicts(raw_events, default_tz=tz)


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
    *,
    default_tz: tzinfo,
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
            start = _normalize_datetime(datetime.fromisoformat(start_str), default_tz)
            end = _normalize_datetime(datetime.fromisoformat(end_str), default_tz)
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
