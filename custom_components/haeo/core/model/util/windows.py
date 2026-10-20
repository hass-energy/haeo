"""Window masks shared by elements that act inside scheduled windows.

A schedule of non-overlapping windows is described by two masks over the
horizon:

- ``in_window`` (per period): 1 where the period lies inside a window.
- ``window_start`` (per boundary): 1 where a window starts. It separates
  windows that touch end to start.

A window still open at the horizon end ends at the final boundary.
"""

import numpy as np
from numpy.typing import NDArray


def window_carry(in_window: NDArray[np.float64], window_start: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return 1 for each period that continues the window of the boundary before it.

    A period continues the window when it is inside a window and no window
    starts at its opening boundary. Per-window accumulators carry their value
    forward across these periods and start from zero across every other one.
    """
    return in_window * (1.0 - window_start[:-1])


def window_end(in_window: NDArray[np.float64], window_start: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return 1 at boundaries 1..T where a window ends.

    A window ends at the last boundary of a run of in-window periods, or at
    a boundary where the next window starts.
    """
    next_in_window = np.append(in_window[1:], 0.0)
    next_continues = next_in_window * (1.0 - window_start[1:])
    return in_window * (1.0 - next_continues)


def window_end_index(in_window: NDArray[np.float64], window_start: NDArray[np.float64]) -> NDArray[np.int64]:
    """Return, for each period, the boundary index where its window ends.

    Periods outside every window map to their own closing boundary.
    """
    ends = window_end(in_window, window_start)
    n_periods = len(in_window)
    end_index = np.arange(1, n_periods + 1, dtype=np.int64)
    for t in range(n_periods - 2, -1, -1):
        if in_window[t] > 0.0 and ends[t] <= 0.0:
            end_index[t] = end_index[t + 1]
    return end_index


__all__ = ["window_carry", "window_end", "window_end_index"]
