"""Tests for building deferrable load windows from calendar boundary data."""

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from custom_components.haeo.core.adapters.calendar_windows import calendar_windows
from custom_components.haeo.core.data.loader.calendar import CalendarWindow
from custom_components.haeo.core.data.loader.calendar_resolver import CalendarBoundaryData
from custom_components.haeo.core.data.util.calendar_fuser import (
    fill_none,
    fuse_window_edges_to_boundaries,
    fuse_windows_to_boundaries,
)

_T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _boundary_data(n_periods: int, events: list[tuple[float, float, float]]) -> CalendarBoundaryData:
    """Fuse (start hour, end hour, value) events onto an hourly horizon."""
    boundaries = [_T0 + timedelta(hours=k) for k in range(n_periods + 1)]
    windows = [
        CalendarWindow(start=_T0 + timedelta(hours=s), end=_T0 + timedelta(hours=e), value=v) for s, e, v in events
    ]

    def _fused(values: list[float | None]) -> np.ndarray:
        return np.array(fill_none(values, 0.0), dtype=np.float64)

    span = _fused(fuse_windows_to_boundaries(windows, boundaries))
    return CalendarBoundaryData(
        presence=(span > 0).astype(np.float64),
        value_span=span,
        value_edge_start=_fused(fuse_window_edges_to_boundaries(windows, boundaries, "start")),
        value_edge_end=_fused(fuse_window_edges_to_boundaries(windows, boundaries, "end")),
        open_since=None,
    )


@pytest.mark.parametrize(
    ("events", "in_window", "window_start", "requirement"),
    [
        pytest.param([], [0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0], id="no_events"),
        pytest.param(
            [(1, 3, 5.0)],
            [0, 1, 1, 0],
            [0, 1, 0, 0, 0],
            [0, 0, 0, 5, 0],
            id="single_window",
        ),
        pytest.param(
            [(0, 1, 2.0), (2, 3, 3.0)],
            [1, 0, 1, 0],
            [0, 0, 1, 0, 0],
            [0, 2, 0, 3, 0],
            id="sequential_windows",
        ),
        pytest.param(
            [(0, 2, 2.0), (2, 4, 3.0)],
            [1, 1, 1, 1],
            [0, 0, 1, 0, 0],
            [0, 0, 2, 0, 3],
            id="adjacent_windows_stay_separate",
        ),
        pytest.param(
            [(0, 3, 2.0), (1, 4, 3.0)],
            [1, 1, 1, 1],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 5],
            id="overlapping_windows_merge",
        ),
        pytest.param(
            [(0, 2, 2.0), (2, 4, 3.0), (1, 3, 1.0)],
            [1, 1, 1, 1],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 6],
            id="bridging_event_merges_adjacent_windows",
        ),
        pytest.param(
            [(2, 10, 4.0)],
            [0, 0, 1, 1],
            [0, 0, 1, 0, 0],
            [0, 0, 0, 0, 4],
            id="window_past_horizon_end_is_due_at_final_boundary",
        ),
        pytest.param(
            [(-2, 2, 4.0)],
            [1, 1, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 4, 0, 0],
            id="window_open_at_horizon_start",
        ),
        pytest.param(
            [(1, 3, 0.0)],
            [0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            id="event_without_energy_is_not_a_window",
        ),
        pytest.param(
            [(0, 2, 2.0), (1, 4, 0.0), (2, 4, 3.0)],
            [1, 1, 1, 1],
            [0, 0, 1, 0, 0],
            [0, 0, 2, 0, 3],
            id="event_without_energy_does_not_bridge",
        ),
    ],
)
def test_calendar_windows(
    events: list[tuple[float, float, float]],
    in_window: list[float],
    window_start: list[float],
    requirement: list[float],
) -> None:
    """Calendar events become non-overlapping windows with requirements at their ends."""
    windows = calendar_windows(_boundary_data(4, events))

    np.testing.assert_allclose(windows.in_window, in_window)
    np.testing.assert_allclose(windows.window_start, window_start)
    np.testing.assert_allclose(windows.requirement, requirement)


def test_calendar_windows_scale_values() -> None:
    """The scale converts event values to energy."""
    windows = calendar_windows(_boundary_data(2, [(0, 1, 100.0)]), scale=0.2)

    np.testing.assert_allclose(windows.requirement, [0.0, 20.0, 0.0])
