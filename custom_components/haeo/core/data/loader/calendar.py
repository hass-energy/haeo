"""Calendar event loading — extract time-windowed values from calendar entities.

Calendar entities in HA expose events with start/end times, summary, location,
and description fields. This loader extracts a numeric value from each event
using a configurable field + parser, producing ``CalendarWindow`` objects that
downstream fusers align to the optimization horizon.

Outside of any window, fused values are None — callers decide how to fill
gaps (e.g. 0.0 for availability, hold-last for a schedule, etc.).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, tzinfo
import re
from typing import TYPE_CHECKING, Final, TypedDict

if TYPE_CHECKING:
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


# Pattern: number (with optional decimal) followed by required unit
# Examples: "50 km", "30mi", "100.5 miles", "15.2 m"
_DISTANCE_PATTERN: Final = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*([a-zA-Zμ]+)\s*$",
)

# Mapping of common distance unit strings to HA UnitOfLength values
_UNIT_ALIASES: Final[dict[str, str]] = {
    "km": "km",
    "kilometer": "km",
    "kilometers": "km",
    "kilometre": "km",
    "kilometres": "km",
    "mi": "mi",
    "mile": "mi",
    "miles": "mi",
    "m": "m",
    "meter": "m",
    "meters": "m",
    "metre": "m",
    "metres": "m",
    "ft": "ft",
    "feet": "ft",
    "foot": "ft",
    "yd": "yd",
    "yard": "yd",
    "yards": "yd",
}


def parse_distance(text: str) -> tuple[float, str] | None:
    """Parse a distance value with unit from text.

    Returns (value, normalized_unit) or None if unparseable.
    """
    match = _DISTANCE_PATTERN.match(text)
    if match is None:
        return None

    value = float(match.group(1))
    unit_str = match.group(2).lower()

    unit = _UNIT_ALIASES.get(unit_str)
    if unit is None:
        return None

    return (value, unit)


def parse_number(text: str) -> float | None:
    """Parse a plain numeric value from text."""
    try:
        return float(text.strip())
    except (ValueError, AttributeError):
        return None


@dataclass(frozen=True)
class CalendarEventData:
    """Minimal event data from a calendar entity."""

    start: datetime
    end: datetime
    summary: str | None = None
    location: str | None = None
    description: str | None = None


type EventValueFn = Callable[[CalendarEventData], float | None]
"""Function that extracts a numeric value from a calendar event.

Returns None if the event should be skipped (no value extractable).
"""


def extract_calendar_windows(
    events: Sequence[CalendarEventData],
    extract_value: EventValueFn,
) -> list[CalendarWindow]:
    """Extract time windows with values from calendar events.

    Args:
        events: Calendar events to process.
        extract_value: Function that extracts a float from each event.
            Return None to skip an event.

    Returns:
        Sorted list of windows. Events with end ≤ start or None value are skipped.

    """
    windows: list[CalendarWindow] = []

    for event in events:
        if event.end <= event.start:
            continue

        value = extract_value(event)
        if value is None:
            continue

        windows.append(CalendarWindow(start=event.start, end=event.end, value=value))

    return sorted(windows, key=lambda w: w.start)


# --- Pre-built value extractors ---

_DEFAULT_TEXT_FIELDS: Final[tuple[str, ...]] = ("location", "summary", "description")


def make_field_fallback_extractor(
    parser: Callable[[str], float | None],
    fields: Sequence[str] = _DEFAULT_TEXT_FIELDS,
) -> EventValueFn:
    """Create an extractor that parses the first text field holding a parseable value.

    Tries fields in order (default: location, summary, description), skipping
    empty fields and fields the parser cannot read. Returns None when no field
    yields a value.
    """

    def _extract(event: CalendarEventData) -> float | None:
        for field in fields:
            text = getattr(event, field, None)
            if text and (value := parser(text)) is not None:
                return value
        return None

    return _extract


def make_distance_extractor(
    energy_per_distance: float,
    target_unit: str,
    convert_distance: Callable[[float, str, str], float] | None = None,
) -> EventValueFn:
    """Create an extractor that parses distance from location and converts to energy.

    Args:
        energy_per_distance: Energy consumption per unit distance (kWh/unit).
        target_unit: Distance unit that energy_per_distance is expressed in.
        convert_distance: Optional unit conversion function.

    Returns:
        EventValueFn that extracts energy (kWh) from an event's location field.

    """

    def _parse_distance_energy(text: str) -> float | None:
        parsed = parse_distance(text)
        if parsed is None:
            return None
        raw_distance, raw_unit = parsed
        if raw_unit != target_unit:
            if convert_distance is None:
                return None
            raw_distance = convert_distance(raw_distance, raw_unit, target_unit)
        return raw_distance * energy_per_distance

    return make_field_fallback_extractor(_parse_distance_energy)


def make_presence_extractor(present_value: float = 1.0) -> EventValueFn:
    """Create an extractor that returns a constant value for any event.

    Useful for binary availability: value during event, None outside.
    """

    def _extract(_event: CalendarEventData) -> float | None:
        return present_value

    return _extract


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
