"""Turn calendar boundary data into deferrable load window parameters."""

from typing import Final, NamedTuple

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.data.loader.calendar_resolver import CalendarBoundaryData

# Tolerance for treating a summed event value as zero.
_EPSILON: Final = 1e-9


class CalendarWindows(NamedTuple):
    """Non-overlapping windows as deferrable load parameters.

    Attributes:
        in_window: 1.0 for each period inside a window (n entries).
        window_start: 1.0 at boundaries where a window starts after the
            horizon start (n+1 entries). A window covering the first period
            counts as open at the horizon start, so it never starts at
            boundary 0.
        requirement: Each window's summed event value at its end boundary
            (n+1 entries). A window running past the horizon end is due at
            the final boundary.

    """

    in_window: NDArray[np.float64]
    window_start: NDArray[np.float64]
    requirement: NDArray[np.float64]


def calendar_windows(calendar: CalendarBoundaryData, scale: float = 1.0) -> CalendarWindows:
    """Build non-overlapping windows from calendar boundary data.

    Only events with a positive value form windows; an event whose text held
    no usable number keeps no window open. Overlapping events merge into a
    single window whose requirement is the sum of their values. Events that
    only touch (one ends at the boundary where the next starts) stay
    separate windows.

    Args:
        calendar: Horizon-aligned calendar arrays.
        scale: Factor converting event values to energy (kWh).

    Returns:
        Window masks and requirements aligned to the horizon.

    """
    span = np.asarray(calendar["value_span"], dtype=np.float64)
    edge_start = np.asarray(calendar["value_edge_start"], dtype=np.float64)
    edge_end = np.asarray(calendar["value_edge_end"], dtype=np.float64)
    n_periods = len(span) - 1

    in_window = (span[:-1] > _EPSILON).astype(np.float64)

    # An interior boundary splits two in-window periods only when no event
    # crosses it: everything covering the earlier period ends there.
    crossing = span[:-2] - edge_end[1:-1]
    split = (in_window[:-1] > 0.0) & (in_window[1:] > 0.0) & (crossing <= _EPSILON)
    opens = (in_window[1:] > 0.0) & (in_window[:-1] <= 0.0)
    window_start = np.concatenate(([0.0], (opens | split).astype(np.float64), [0.0]))

    requirement = np.zeros(n_periods + 1, dtype=np.float64)
    first = 0
    for t in range(n_periods):
        if in_window[t] <= 0.0:
            continue
        if t == 0 or window_start[t] > 0.0 or in_window[t - 1] <= 0.0:
            first = t
        ends_here = t == n_periods - 1 or in_window[t + 1] <= 0.0 or window_start[t + 1] > 0.0
        if ends_here:
            requirement[t + 1] = float(edge_start[first : t + 1].sum()) * scale

    return CalendarWindows(in_window=in_window, window_start=window_start, requirement=requirement)


__all__ = ["CalendarWindows", "calendar_windows"]
