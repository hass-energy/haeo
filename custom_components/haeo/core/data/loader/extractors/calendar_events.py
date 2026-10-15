"""Calendar events as a stepped forecast.

A Home Assistant calendar's state only shows its current or next event, so
the integration fetches the horizon's events and injects them into the
state as the ``haeo_events`` attribute. A state carrying them reads as a
forecast like any forecast sensor: each event's number while it runs,
summed where events overlap, and zero outside events.

The value is a number with its unit, such as "5 kW" or "0.30 $/kWh", read
from the event's location, summary, or description, and converted to base
units like a sensor reading. A bare number is rejected rather than taken to
be in base units. An event without a number counts as zero.
"""

from collections.abc import Sequence
from datetime import timedelta
from typing import Final, Literal, TypeGuard

from custom_components.haeo.core.data.loader.calendar import (
    CALENDAR_EVENTS_ATTRIBUTE,
    event_quantity,
    load_calendar_events,
)
from custom_components.haeo.core.data.util.input_values import InputError
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
    def extract(state: EntityState) -> tuple[Sequence[tuple[float, float]] | float, str | None, DeviceClass | None]:
        """Return the events' values in base units as step-function points, or zero when there are none.

        Each change in the summed value gets a point at the old value and one at
        the new value at the same time, which the caller separates so the fuser
        does not interpolate between them. Zero points well before and after
        the events stop the series from repeating across the horizon.

        Raises:
            InputError: If an event's number has no unit, or events' units
                convert to different base units.

        """
        events = load_calendar_events(state) or []
        changes: dict[float, float] = {}
        base_units: set[str] = set()
        for event in events:
            quantity = event_quantity(event)
            if quantity is None:
                continue
            value, unit = quantity
            if unit is None:
                raise InputError(
                    translation_key="calendar_value_without_unit",
                    translation_placeholders={"value": f"{value:g}"},
                )
            factor, base_unit, _ = base_unit_conversion(unit, None)
            base_units.add(str(base_unit))
            start, end = event.start.timestamp(), event.end.timestamp()
            changes[start] = changes.get(start, 0.0) + value * factor
            changes[end] = changes.get(end, 0.0) - value * factor
        if len(base_units) > 1:
            raise InputError(
                translation_key="calendar_mixed_units",
                translation_placeholders={"units": ", ".join(sorted(base_units))},
            )
        base_unit = next(iter(base_units), None)
        if not changes:
            return 0.0, base_unit, None

        timestamps = sorted(changes)
        points: list[tuple[float, float]] = [(timestamps[0] - _ZERO_PADDING, 0.0)]
        level = 0.0
        for timestamp in timestamps:
            points.append((timestamp, level))
            level += changes[timestamp]
            points.append((timestamp, level))
        points.append((timestamps[-1] + _ZERO_PADDING, 0.0))
        return points, base_unit, None


__all__ = ["DOMAIN", "Format", "Parser"]
