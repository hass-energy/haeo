"""Resolve a meter input: how much its meters rose since the open calendar window began.

A meter is a running total, such as an energy sensor that only counts up.
Its state only says what it reads now, and many meters reset (an "energy
today" sensor returns to zero at midnight), so the reading alone cannot say
how much it rose since a window started. The integration reads the meter's
recorded totals, which carry on through resets, and injects them into the
meter's state as ``(time, total)`` pairs, the same way calendar events are
injected into a calendar's state. A meter input reads its window calendars
as well as its meters, so its captured source states hold both, and
diagnostics replay the same value.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
import math
from typing import Final

from custom_components.haeo.core.data.util.field_units import check_source_unit
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.state import EntityState, StateMachine
from custom_components.haeo.core.units import DeviceClass, base_unit_conversion

from .calendar import CalendarEventData, load_calendar_events, open_window_start

# State attribute carrying a meter's recorded totals, injected by the integration
METER_TOTALS_ATTRIBUTE: Final = "haeo_meter_totals"

# A meter's running total at a time: (time, total), POSIX seconds
type MeterTotal = tuple[float, float]


def read_meter_totals(state: EntityState | None) -> list[MeterTotal] | None:
    """Return the totals injected into a meter's state, oldest first, or None when it carries none."""
    raw = state.attributes.get(METER_TOTALS_ATTRIBUTE) if state is not None else None
    if not isinstance(raw, Sequence) or isinstance(raw, str):
        return None
    totals: list[MeterTotal] = []
    for item in raw:
        if not isinstance(item, Sequence) or isinstance(item, str) or len(item) != 2:  # noqa: PLR2004 (a pair)
            return None
        at, total = item
        if isinstance(at, bool) or isinstance(total, bool) or not isinstance(at, (int, float)):
            return None
        if not isinstance(total, (int, float)) or not math.isfinite(total):
            return None
        totals.append((float(at), float(total)))
    return sorted(totals)


def rise_since(totals: Sequence[MeterTotal], since: float) -> float | None:
    """Return how much a meter rose from its total at *since* to its latest total.

    When the totals start after *since*, as when a window began before the
    recorded totals reach back, the rise counts from the earliest total, the
    most the meter is known to have risen. Returns None without totals. A
    meter whose totals fell, as a replaced meter's might, rose nothing.
    """
    if not totals:
        return None
    before = [total for at, total in totals if at <= since]
    start = before[-1] if before else totals[0][1]
    return max(totals[-1][1] - start, 0.0)


def totals_since(totals: Sequence[MeterTotal], since: float | None) -> list[MeterTotal]:
    """Return the totals a rise since *since* reads: the one it rises from and the latest.

    The rise starts from the last total at or before *since*, or the
    earliest when the totals start later. With no window open there is no
    rise to read, so only the latest total is kept.
    """
    if not totals or since is None:
        return list(totals[-1:])
    start = totals[0]
    for total in totals:
        if total[0] > since:
            break
        start = total
    return [start] if start == totals[-1] else [start, totals[-1]]


def resolve_meter(
    entity_ids: Sequence[str], output_type: OutputType, sm: StateMachine, forecast_times: Sequence[float]
) -> float | None:
    """Return how much the meters rose since the window open at the horizon start began, in base units.

    The entities are the input's meters and its window calendars, told
    apart by the calendars' events. Overlapping events chain into one
    window, so the rise counts from the earliest start among the events
    open at the horizon start. Nothing has been delivered toward a window
    that is not open, so the rise is zero then. Returns None when a source
    has no state or a meter carries no totals.

    Raises:
        InputError: If a meter's unit cannot convert to the field's unit.

    """
    states = [sm.get(entity_id) for entity_id in entity_ids]
    if not forecast_times or any(state is None for state in states):
        return None
    events: list[CalendarEventData] = []
    meters: list[EntityState] = []
    for state in states:
        found = load_calendar_events(state, sm.time_zone)
        if found is not None:
            events.extend(found)
        elif state is not None:
            meters.append(state)
    opened = open_window_start(events, datetime.fromtimestamp(forecast_times[0], tz=UTC))
    if opened is None:
        return 0.0
    rises = [_rise_in_base_unit(meter, opened, output_type) for meter in meters]
    return None if any(rise is None for rise in rises) else sum(rise for rise in rises if rise is not None)


def _rise_in_base_unit(state: EntityState, since: float, output_type: OutputType) -> float | None:
    """Return how much a meter rose since a time, converted from its unit like its reading."""
    rise = rise_since(read_meter_totals(state) or [], since)
    if rise is None:
        return None
    unit = state.attributes.get("unit_of_measurement")
    factor, base_unit, _ = base_unit_conversion(
        unit if isinstance(unit, str) else None, DeviceClass.of(state.attributes.get("device_class"))
    )
    check_source_unit(None if base_unit is None else str(base_unit), output_type)
    return rise * factor


__all__ = [
    "METER_TOTALS_ATTRIBUTE",
    "MeterTotal",
    "read_meter_totals",
    "resolve_meter",
    "rise_since",
    "totals_since",
]
