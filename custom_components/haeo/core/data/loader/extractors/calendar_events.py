"""Calendar events as a stepped forecast.

A Home Assistant calendar's state only shows its current or next event, so
the integration fetches the horizon's events and injects them into the
state as the ``haeo_events`` attribute. A state carrying them reads as a
forecast like any forecast sensor: each event's value while it runs,
summed where events overlap, and zero outside events.

The value is a number with its unit, such as "5 kW" or "0.30 $/kWh", read
from the event's location, summary, or description, and converted to the
input's unit like a sensor reading. A calendar without valued events is a
forecast with no points, which adds nothing. An event whose value the input cannot
use, such as a bare number, is ignored like an event without a number, so one
mistyped event does not stop the rest of the calendar from loading.
"""

from collections.abc import Sequence
from datetime import timedelta
from typing import Final, Literal, TypeGuard

from custom_components.haeo.core.data.loader.calendar import (
    CALENDAR_EVENTS_ATTRIBUTE,
    CalendarEventData,
    event_quantity,
    event_value,
    load_calendar_events,
)
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import DeviceClass, base_unit_conversion

Format = Literal["calendar"]
DOMAIN: Format = "calendar"

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
    def extract(
        state: EntityState, output_type: OutputType | None = None
    ) -> tuple[Sequence[tuple[float, float]] | float, str | None, DeviceClass | None]:
        """Return the events' values as step-function points, or no points when there are none.

        With the input's output type, each value converts to the input's unit
        and the series carries no unit to convert further. Without it, values
        convert to base units, keeping the events whose unit has the same base
        unit as the first event's.

        Each change in the summed value gets a point at the old value and one at
        the new value at the same time, which the caller separates so the fuser
        does not interpolate between them. Zero points well before and after
        the events stop the series from repeating across the horizon.
        """
        events = load_calendar_events(state) or []
        if output_type is None:
            values, unit = _base_unit_values(events)
        else:
            values, unit = [(event, event_value(event, output_type)) for event in events], None

        changes: dict[float, float] = {}
        for event, value in values:
            if not value:
                continue
            start, end = event.start.timestamp(), event.end.timestamp()
            changes[start] = changes.get(start, 0.0) + value
            changes[end] = changes.get(end, 0.0) - value
        if not changes:
            return [], unit, None

        timestamps = sorted(changes)
        points: list[tuple[float, float]] = [(timestamps[0] - _ZERO_PADDING, 0.0)]
        level = 0.0
        for timestamp in timestamps:
            points.append((timestamp, level))
            level += changes[timestamp]
            points.append((timestamp, level))
        points.append((timestamps[-1] + _ZERO_PADDING, 0.0))
        return points, unit, None


def _base_unit_values(
    events: Sequence[CalendarEventData],
) -> tuple[list[tuple[CalendarEventData, float | None]], str | None]:
    """Return each event's value in base units, and the base unit they share."""
    values: list[tuple[CalendarEventData, float | None]] = []
    shared_unit: str | None = None
    for event in events:
        quantity = event_quantity(event)
        if quantity is None or quantity[1] is None:
            continue
        factor, base_unit, _ = base_unit_conversion(quantity[1], None)
        shared_unit = shared_unit or str(base_unit)
        if str(base_unit) == shared_unit:
            values.append((event, quantity[0] * factor))
    return values, shared_unit


__all__ = ["DOMAIN", "Format", "Parser"]
