"""Calendar event loading — extract time-windowed values from calendar entities.

Calendar entities in HA expose events with start/end times, summary, location,
and description fields. This loader extracts a numeric value from each event
using a configurable field + parser, producing (timestamp, value|None) pairs
that downstream fusers can align to the optimization horizon.

Outside of any event window, the value is None — callers decide how to fill
gaps (e.g. 0.0 for availability, hold-last for a schedule, etc.).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import re
from typing import TYPE_CHECKING, Any, Final

from custom_components.haeo.core.schema.calendar_value import CalendarEventDict

if TYPE_CHECKING:
    from custom_components.haeo.core.schema.calendar_value import CalendarValue
    from custom_components.haeo.core.state import StateMachine


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

    def _extract(event: CalendarEventData) -> float | None:
        if not event.location:
            return None
        parsed = parse_distance(event.location)
        if parsed is None:
            return None
        raw_distance, raw_unit = parsed
        if raw_unit != target_unit and convert_distance is not None:
            raw_distance = convert_distance(raw_distance, raw_unit, target_unit)
        return raw_distance * energy_per_distance

    return _extract


def make_presence_extractor(present_value: float = 1.0) -> EventValueFn:
    """Create an extractor that returns a constant value for any event.

    Useful for binary availability: value during event, None outside.
    """

    def _extract(_event: CalendarEventData) -> float | None:
        return present_value

    return _extract


def load_calendar_events(
    value: CalendarValue,
    sm: StateMachine,
) -> list[CalendarEventData]:
    """Load calendar events from a CalendarValue schema field.

    Two paths based on type discrimination:
    - If ``value["events"]`` is populated (diagnostic replay), parse directly
    - Otherwise, load from the StateMachine (live HA entity)

    The live path reads events from the entity's ``haeo_events`` attribute,
    which must be injected by the HA-level calendar service caller before
    the core loader sees it.

    Args:
        value: Calendar schema value with entity_id and optional captured events.
        sm: State machine for entity state lookup.

    Returns:
        List of CalendarEventData objects.

    """
    # Path 1: Events already captured (diagnostic replay / scenario test)
    if value.get("events") is not None:
        return _parse_event_dicts(value["events"])

    # Path 2: Load from entity state
    entity_id = value["value"]
    state = sm.get(entity_id)
    if state is None:
        return []

    # Events are expected in the haeo_events attribute, injected by the
    # HA-level adapter before the core loader runs.
    raw_events = state.attributes.get("haeo_events")
    if not isinstance(raw_events, list):
        return []

    return _parse_event_dicts(raw_events)


def capture_calendar_events(
    events: list[CalendarEventData],
) -> list[CalendarEventDict]:
    """Serialize calendar events for diagnostics capture.

    Produces the format stored in CalendarValue.events and in
    entity state attributes for diagnostic replay.
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
    raw_events: Sequence[Any],
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
            start = datetime.fromisoformat(start_str)
            end = datetime.fromisoformat(end_str)
        except (ValueError, TypeError):
            continue
        events.append(
            CalendarEventData(
                start=start,
                end=end,
                summary=raw.get("summary"),
                location=raw.get("location"),
                description=raw.get("description"),
            )
        )
    return events
