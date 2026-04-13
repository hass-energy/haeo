"""Calendar event loading and trip window extraction."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import re
from typing import Final


@dataclass(frozen=True)
class TripWindow:
    """A trip extracted from a calendar event."""

    start: datetime
    end: datetime
    distance: float
    energy_kwh: float


# Pattern: number (with optional decimal) followed by required unit
# Examples: "50 km", "30mi", "100.5 miles", "15.2 m"
_DISTANCE_PATTERN: Final = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*([a-zA-Zμ]+)\s*$",
)

# Mapping of common distance unit strings to HA UnitOfLength values
# HA uses: km, mi, m, cm, mm, yd, ft, in
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


def parse_distance(location: str) -> tuple[float, str] | None:
    """Parse a distance value with unit from a calendar event location field.

    Returns (value, unit) where unit is a normalized HA distance unit string,
    or None if the location cannot be parsed.
    """
    match = _DISTANCE_PATTERN.match(location)
    if match is None:
        return None

    value = float(match.group(1))
    unit_str = match.group(2).lower()

    unit = _UNIT_ALIASES.get(unit_str)
    if unit is None:
        return None

    return (value, unit)


def extract_trip_windows(
    events: list[TripEventData],
    energy_per_distance: float,
    distance_unit: str,
    ha_default_distance_unit: str,  # noqa: ARG001
    convert_distance: ConvertDistanceFn | None = None,
) -> list[TripWindow]:
    """Extract trip windows from calendar events.

    Args:
        events: Calendar events with start, end, location fields.
        energy_per_distance: Energy consumption per unit distance (kWh/unit).
        distance_unit: The unit that energy_per_distance is expressed in.
        ha_default_distance_unit: The HA instance's default distance unit.
        convert_distance: Optional function to convert between distance units.
            Signature: (value, from_unit, to_unit) -> converted_value.

    Returns:
        Sorted list of trip windows with computed energy requirements.

    """
    trips: list[TripWindow] = []

    for event in events:
        start = event.start
        end = event.end

        if end <= start:
            continue

        distance = 0.0
        if event.location:
            parsed = parse_distance(event.location)
            if parsed is not None:
                raw_distance, raw_unit = parsed
                # Convert to the same unit as energy_per_distance
                if raw_unit != distance_unit and convert_distance is not None:
                    raw_distance = convert_distance(raw_distance, raw_unit, distance_unit)
                distance = raw_distance

        energy = distance * energy_per_distance

        trips.append(TripWindow(start=start, end=end, distance=distance, energy_kwh=energy))

    return sorted(trips, key=lambda t: t.start)


@dataclass(frozen=True)
class TripEventData:
    """Minimal event data extracted from a calendar event."""

    start: datetime
    end: datetime
    location: str | None


type ConvertDistanceFn = Callable[[float, str, str], float]
