"""Resolve calendar schema values into horizon-aligned boundary arrays.

Bridges the calendar event loader and window fuser to the field-resolution
pipeline: a ``CalendarValue`` plus a ``CalendarFieldHint`` become a
``CalendarBoundaryData`` bundle of numpy arrays aligned to the optimization
horizon boundaries.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, TypedDict

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
from custom_components.haeo.core.units import DeviceClass, convert_to_base_unit

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

    from custom_components.haeo.core.schema.calendar_value import CalendarValue
    from custom_components.haeo.core.schema.field_hints import CalendarFieldHint
    from custom_components.haeo.core.state import StateMachine


class CalendarBoundaryData(TypedDict):
    """Horizon-aligned arrays resolved from a calendar field.

    All arrays have n+1 entries, one per horizon boundary. Values are the
    per-event numbers extracted by the field's calendar parser (distances are
    normalized to kilometres); events without a parseable value contribute 0.0
    while still marking their window present.

    Attributes:
        open_since: POSIX time the window open at the horizon start began, or
            None when no window is open then. Only events with a positive
            value count, and overlapping events chain into one window, so a
            window that began before the horizon keeps its true start.
        presence: 1.0 at boundaries covered by any event window, else 0.0.
        value_span: Sum of active window values at each boundary, 0.0 outside.
        value_edge_start: Each window's value placed at its start boundary
            (floored to the containing period), summed on collision.
        value_edge_end: Each window's value placed at its end boundary
            (ceiled to the containing period), summed on collision.

    """

    presence: NDArray[np.float64]
    value_span: NDArray[np.float64]
    value_edge_start: NDArray[np.float64]
    value_edge_end: NDArray[np.float64]
    open_since: float | None


def is_calendar_boundary_data(value: object) -> bool:
    """Return True when *value* looks like resolved calendar boundary data."""
    return isinstance(value, dict) and set(value) == {
        "presence",
        "value_span",
        "value_edge_start",
        "value_edge_end",
        "open_since",
    }


def _convert_distance(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a distance between length units via their kilometre factors."""
    km, _, _ = convert_to_base_unit(value, from_unit, DeviceClass.DISTANCE)
    km_per_target, _, _ = convert_to_base_unit(1.0, to_unit, DeviceClass.DISTANCE)
    return km / km_per_target


def _parser_for(hint: CalendarFieldHint) -> EventValueFn:
    """Return the event value extractor selected by a calendar hint."""
    if hint.parser == "distance":
        return make_distance_extractor(
            energy_per_distance=1.0,
            target_unit="km",
            convert_distance=_convert_distance,
        )
    if hint.parser == "number":
        return make_field_fallback_extractor(parse_number)
    return make_presence_extractor()


def _extractor_for(hint: CalendarFieldHint) -> EventValueFn:
    """Return an extractor that keeps every event window.

    An event's window is meaningful on its own (the vehicle is away, the load
    may run), so an event whose text holds no parseable value still occupies
    its window, contributing a value of 0.0.
    """
    parse = _parser_for(hint)

    def _extract(event: CalendarEventData) -> float:
        value = parse(event)
        return 0.0 if value is None else value

    return _extract


def _open_since(windows: Sequence[CalendarWindow], at: datetime) -> float | None:
    """Return when the window open at *at* began, or None when none is open.

    *windows* are sorted by start. Positive-valued events that overlap chain
    into one window; events that only touch stay separate, matching how trip
    windows are built.
    """
    groups: list[tuple[datetime, datetime]] = []
    for window in (w for w in windows if w.value > 0.0):
        if groups and window.start < groups[-1][1]:
            groups[-1] = (groups[-1][0], max(groups[-1][1], window.end))
        else:
            groups.append((window.start, window.end))
    return next((start.timestamp() for start, end in groups if start <= at < end), None)


def resolve_calendar_field(
    value: CalendarValue,
    calendar_hint: CalendarFieldHint,
    sm: StateMachine,
    forecast_times: Sequence[float],
) -> CalendarBoundaryData | None:
    """Resolve a calendar schema value into horizon-aligned boundary arrays.

    Returns None when the calendar entity is unavailable and no captured
    events exist, so the caller can mark the field as not loaded. An
    available calendar with no events resolves to all-zero arrays.
    """
    if value.get("events") is None and sm.get(value["value"]) is None:
        return None

    events = load_calendar_events(value, sm)
    windows = extract_calendar_windows(events, _extractor_for(calendar_hint))
    boundaries = [datetime.fromtimestamp(ts, tz=UTC) for ts in forecast_times]

    presence_windows = [CalendarWindow(start=w.start, end=w.end, value=1.0) for w in windows]
    presence = np.minimum(
        np.array(fill_none(fuse_windows_to_boundaries(presence_windows, boundaries), 0.0), dtype=np.float64),
        1.0,
    )

    def _fused(values: list[float | None]) -> NDArray[np.float64]:
        return np.array(fill_none(values, 0.0), dtype=np.float64)

    return CalendarBoundaryData(
        presence=presence,
        value_span=_fused(fuse_windows_to_boundaries(windows, boundaries)),
        value_edge_start=_fused(fuse_window_edges_to_boundaries(windows, boundaries, "start")),
        value_edge_end=_fused(fuse_window_edges_to_boundaries(windows, boundaries, "end")),
        open_since=_open_since(windows, boundaries[0]),
    )


__all__ = [
    "CalendarBoundaryData",
    "is_calendar_boundary_data",
    "resolve_calendar_field",
]
