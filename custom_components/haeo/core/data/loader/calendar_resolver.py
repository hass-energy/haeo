"""Resolve calendar events into horizon-aligned input series.

Bridges the calendar event loader and window fuser to the field-resolution
pipeline: an input with a ``CalendarFieldHint`` reads the events injected
into its calendar entity's state and resolves the one series its projection
asks for, aligned to the optimization horizon.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import numpy as np

from custom_components.haeo.core.data.loader.calendar import event_windows, load_calendar_events
from custom_components.haeo.core.data.util.calendar_fuser import (
    fill_none,
    fuse_window_edges_to_boundaries,
    fuse_windows_to_boundaries,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

    from custom_components.haeo.core.model.const import OutputType
    from custom_components.haeo.core.schema.field_hints import CalendarFieldHint
    from custom_components.haeo.core.state import StateMachine


def _fused(values: list[float | None]) -> NDArray[np.float64]:
    return np.array(fill_none(values, 0.0), dtype=np.float64)


def _windows(
    count_span: NDArray[np.float64], count_end: NDArray[np.float64], value_start: NDArray[np.float64]
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Return each period's window flag, each boundary's start flag, and each window's due value.

    Every event is a window, including one whose text holds no value, which
    is due nothing. Overlapping events merge into a single window due their
    summed value; events that only touch (one ends at the boundary where the
    next starts) stay separate windows. A window covering the first period is
    open at the horizon start, so it never starts at boundary 0, and a window
    running past the horizon is due at its end.

    Args:
        count_span: Number of events covering each boundary.
        count_end: Number of events ending at each boundary.
        value_start: Summed event values starting at each boundary.

    """
    n_periods = len(count_span) - 1
    active = (count_span[:-1] > 0.0).astype(np.float64)

    # An interior boundary splits two in-window periods only when no event
    # crosses it: every event covering the earlier period ends there.
    crossing = count_span[:-2] - count_end[1:-1]
    split = (active[:-1] > 0.0) & (active[1:] > 0.0) & (crossing <= 0.0)
    opens = (active[1:] > 0.0) & (active[:-1] <= 0.0)
    starts = np.concatenate(([0.0], (opens | split).astype(np.float64), [0.0]))

    due = np.zeros(n_periods + 1, dtype=np.float64)
    first = 0
    for t in np.flatnonzero(active > 0.0):
        if t == 0 or starts[t] > 0.0 or active[t - 1] <= 0.0:
            first = t
        if t == n_periods - 1 or active[t + 1] <= 0.0 or starts[t + 1] > 0.0:
            due[t + 1] = float(value_start[first : t + 1].sum())

    return active, starts, due


def resolve_calendar(
    entity_ids: Sequence[str],
    hint: CalendarFieldHint,
    output_type: OutputType,
    sm: StateMachine,
    forecast_times: Sequence[float],
) -> NDArray[np.float64] | None:
    """Resolve the series a calendar input's projection asks for from its calendars' events.

    The events of every calendar the input reads count together. Returns
    None when a calendar's state is missing or carries no injected events,
    so the input reads as not loaded. Calendars with no events in the horizon
    resolve to all zeros. Only the due projection reads event values, each
    converted from the unit typed with it to the input's unit; an event whose
    value the input cannot use is still a window, due nothing.
    """
    calendars = [load_calendar_events(sm.get(entity_id)) for entity_id in entity_ids]
    if any(events is None for events in calendars):
        return None
    windows = event_windows([event for events in calendars if events for event in events], output_type)
    counted = [replace(window, value=1.0) for window in windows]
    boundaries = [datetime.fromtimestamp(ts, tz=UTC) for ts in forecast_times]

    active, starts, due = _windows(
        _fused(fuse_windows_to_boundaries(counted, boundaries)),
        _fused(fuse_window_edges_to_boundaries(counted, boundaries, "end")),
        _fused(fuse_window_edges_to_boundaries(windows, boundaries, "start")),
    )
    return {"window_active": active, "window_starts": starts, "window_due": due}[hint.projection]


__all__ = ["resolve_calendar"]
