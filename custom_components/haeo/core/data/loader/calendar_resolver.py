"""Resolve calendar events into horizon-aligned input series.

Bridges the calendar event loader and window fuser to the field-resolution
pipeline: an input with a ``CalendarFieldHint`` reads the events injected
into its calendar entity's state and resolves the one series its projection
asks for, aligned to the optimization horizon.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

import numpy as np

from custom_components.haeo.core.data.loader.calendar import (
    CalendarEventData,
    CalendarWindow,
    EventValueFn,
    extract_calendar_windows,
    load_calendar_events,
    make_distance_extractor,
    make_field_fallback_extractor,
    make_presence_extractor,
    parse_number,
)
from custom_components.haeo.core.data.util.calendar_fuser import (
    fill_none,
    fuse_window_edges_to_boundaries,
    fuse_windows_to_boundaries,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

    from custom_components.haeo.core.schema.field_hints import CalendarFieldHint, CalendarParser
    from custom_components.haeo.core.state import StateMachine

# Kilometres per supported distance unit, used to normalize parsed distances
# without importing Home Assistant's unit converters into the core layer.
_KM_PER_UNIT: Final[dict[str, float]] = {
    "km": 1.0,
    "mi": 1.609344,
    "m": 0.001,
    "ft": 0.0003048,
    "yd": 0.0009144,
}

# Tolerance for treating a summed event value as zero
_EPSILON: Final = 1e-9


def _convert_distance(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a distance between supported units via the kilometre table."""
    return value * _KM_PER_UNIT[from_unit] / _KM_PER_UNIT[to_unit]


def _extractor_for(parser: CalendarParser) -> EventValueFn:
    """Return an extractor that keeps every event, valuing one without a parseable value at 0.0.

    An event's window is meaningful on its own (the vehicle is away), so an
    event whose text holds no usable value still covers its periods.
    """
    if parser == "distance":
        parse = make_distance_extractor(energy_per_distance=1.0, target_unit="km", convert_distance=_convert_distance)
    elif parser == "number":
        parse = make_field_fallback_extractor(parse_number)
    else:
        parse = make_presence_extractor()

    def _extract(event: CalendarEventData) -> float:
        value = parse(event)
        return 0.0 if value is None else value

    return _extract


def _fused(values: list[float | None]) -> NDArray[np.float64]:
    return np.array(fill_none(values, 0.0), dtype=np.float64)


def _windows(
    span: NDArray[np.float64], edge_start: NDArray[np.float64], edge_end: NDArray[np.float64]
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Return each period's window flag, each boundary's start flag, and each window's due value.

    Only events with a positive value form windows. Overlapping events merge
    into a single window whose value is their sum; events that only touch (one
    ends at the boundary where the next starts) stay separate windows. A window
    covering the first period is open at the horizon start, so it never starts
    at boundary 0, and a window running past the horizon is due at its end.
    """
    n_periods = len(span) - 1
    active = (span[:-1] > _EPSILON).astype(np.float64)

    # An interior boundary splits two in-window periods only when no event
    # crosses it: everything covering the earlier period ends there.
    crossing = span[:-2] - edge_end[1:-1]
    split = (active[:-1] > 0.0) & (active[1:] > 0.0) & (crossing <= _EPSILON)
    opens = (active[1:] > 0.0) & (active[:-1] <= 0.0)
    starts = np.concatenate(([0.0], (opens | split).astype(np.float64), [0.0]))

    due = np.zeros(n_periods + 1, dtype=np.float64)
    first = 0
    for t in range(n_periods):
        if active[t] <= 0.0:
            continue
        if t == 0 or starts[t] > 0.0 or active[t - 1] <= 0.0:
            first = t
        if t == n_periods - 1 or active[t + 1] <= 0.0 or starts[t + 1] > 0.0:
            due[t + 1] = float(edge_start[first : t + 1].sum())

    return active, starts, due


def resolve_calendar(
    entity_id: str,
    hint: CalendarFieldHint,
    sm: StateMachine,
    forecast_times: Sequence[float],
) -> NDArray[np.float64] | None:
    """Resolve the series a calendar input's projection asks for from its calendar's events.

    Returns None when the calendar's state is missing or carries no injected
    events, so the input reads as not loaded. A calendar with no events in
    the horizon resolves to all zeros.
    """
    events = load_calendar_events(sm.get(entity_id))
    if events is None:
        return None
    windows = extract_calendar_windows(events, _extractor_for(hint.parser))
    boundaries = [datetime.fromtimestamp(ts, tz=UTC) for ts in forecast_times]

    if hint.projection == "presence":
        presence_windows = [CalendarWindow(start=w.start, end=w.end, value=1.0) for w in windows]
        return np.minimum(_fused(fuse_windows_to_boundaries(presence_windows, boundaries))[:-1], 1.0)

    active, starts, due = _windows(
        _fused(fuse_windows_to_boundaries(windows, boundaries)),
        _fused(fuse_window_edges_to_boundaries(windows, boundaries, "start")),
        _fused(fuse_window_edges_to_boundaries(windows, boundaries, "end")),
    )
    if hint.projection == "window_active":
        return active
    if hint.projection == "window_starts":
        return starts
    return due


__all__ = ["resolve_calendar"]
