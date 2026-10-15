"""Calendar events as a stepped forecast.

A Home Assistant calendar's state only shows its current or next event, so
the integration fetches the horizon's events and injects them into the
state as the ``haeo_events`` attribute. A state carrying them reads as a
forecast like any forecast sensor: each event's number while it runs,
summed where events overlap, and zero outside events.

The number is read from the event's location, summary, or description, in
the unit of the field the calendar feeds. An event without one counts as
zero.
"""

from collections.abc import Sequence
from datetime import timedelta
from typing import Final, Literal, TypeGuard

from custom_components.haeo.core.data.loader.calendar import (
    CALENDAR_EVENTS_ATTRIBUTE,
    load_calendar_events,
    make_field_fallback_extractor,
    parse_number,
)
from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import DeviceClass

Format = Literal["calendar"]
DOMAIN: Format = "calendar"

_parse_value = make_field_fallback_extractor(parse_number)

# A forecast shorter than the horizon repeats daily to fill it, but a calendar
# is zero outside its events, so its series reaches this far past them.
_ZERO_PADDING: Final = timedelta(days=60).total_seconds()


class Parser:
    """Parser reading the events injected into a calendar entity's state as a stepped forecast."""

    DOMAIN: Format = DOMAIN

    @staticmethod
    def detect(state: EntityState) -> TypeGuard[EntityState]:
        """Return True when the state carries injected calendar events."""
        return isinstance(state.attributes.get(CALENDAR_EVENTS_ATTRIBUTE), list)

    @staticmethod
    def extract(state: EntityState) -> tuple[Sequence[tuple[float, float]] | float, None, DeviceClass | None]:
        """Return the events' values as step-function points, or zero when there are none.

        Each change in the summed value gets a point at the old value and one at
        the new value at the same time, which the caller separates so the fuser
        does not interpolate between them. Zero points well before and after
        the events stop the series from repeating across the horizon.
        """
        events = load_calendar_events(state) or []
        changes: dict[float, float] = {}
        for event in events:
            value = _parse_value(event)
            if not value:
                continue
            start, end = event.start.timestamp(), event.end.timestamp()
            changes[start] = changes.get(start, 0.0) + value
            changes[end] = changes.get(end, 0.0) - value
        if not changes:
            return 0.0, None, None

        timestamps = sorted(changes)
        points: list[tuple[float, float]] = [(timestamps[0] - _ZERO_PADDING, 0.0)]
        level = 0.0
        for timestamp in timestamps:
            points.append((timestamp, level))
            level += changes[timestamp]
            points.append((timestamp, level))
        points.append((timestamps[-1] + _ZERO_PADDING, 0.0))
        return points, None, None


__all__ = ["DOMAIN", "Format", "Parser"]
