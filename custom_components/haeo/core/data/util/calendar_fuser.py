"""Fuse calendar windows into horizon-aligned time-series arrays.

Takes a list of CalendarWindow objects and a sequence of horizon boundary
timestamps, and produces a boundary-aligned array of values. Boundaries
outside any window get None — the caller decides the fill strategy.
"""

from __future__ import annotations

import bisect
from collections.abc import Sequence
from datetime import datetime

from custom_components.haeo.core.data.loader.calendar import CalendarWindow


def fuse_windows_to_boundaries(
    windows: list[CalendarWindow],
    horizon_times: Sequence[datetime],
) -> list[float | None]:
    """Convert calendar windows into a boundary-aligned value array.

    For each boundary point, returns the value of the window that contains it,
    or None if the boundary is outside all windows.

    Aliasing rules:
    - Window start snaps to the start of the containing period (floor)
    - Window end snaps to the end of the containing period (ceiling)
    - This ensures clean period boundaries with no partial overlaps

    When multiple windows overlap at a boundary, the last window's value wins.

    Args:
        windows: Sorted list of calendar windows (may overlap).
        horizon_times: n+1 boundary timestamps defining n periods.

    Returns:
        List of n+1 values (float or None), one per boundary.

    """
    n_boundaries = len(horizon_times)
    if n_boundaries == 0:
        return []

    values: list[float | None] = [None] * n_boundaries

    for window in windows:
        start_idx = _floor_boundary_index(window.start, horizon_times)
        end_idx = _ceil_boundary_index(window.end, horizon_times)

        if start_idx >= n_boundaries or end_idx <= 0:
            continue

        start_idx = max(start_idx, 0)
        end_idx = min(end_idx, n_boundaries)

        for i in range(start_idx, end_idx):
            values[i] = window.value

    return values


def fill_none(
    values: list[float | None],
    default: float,
) -> list[float]:
    """Replace None values with a default.

    Common fill strategies:
    - fill_none(values, 0.0)  — zero outside events (e.g. energy demand)
    - fill_none(values, 1.0)  — one outside events (e.g. connected flag)
    """
    return [default if v is None else v for v in values]


def _floor_boundary_index(dt: datetime, boundaries: Sequence[datetime]) -> int:
    """Find the boundary index at or before dt (floor to period start)."""
    idx = bisect.bisect_right(boundaries, dt) - 1
    return max(idx, 0)


def _ceil_boundary_index(dt: datetime, boundaries: Sequence[datetime]) -> int:
    """Find the boundary index at or after dt (ceil to period end)."""
    idx = bisect.bisect_left(boundaries, dt)
    return min(idx, len(boundaries))
