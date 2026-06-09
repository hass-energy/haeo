"""Tests for calendar window fusion to horizon boundaries."""

from datetime import UTC, datetime

import pytest

from custom_components.haeo.core.data.loader.calendar import CalendarWindow
from custom_components.haeo.core.data.util.calendar_fuser import (
    fill_none,
    fuse_window_edges_to_boundaries,
    fuse_windows_to_boundaries,
)


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2025, 1, 1, hour, minute, tzinfo=UTC)


def _boundaries(*hours: int) -> list[datetime]:
    return [_dt(h) for h in hours]


def _window(start_h: int, end_h: int, value: float = 1.0) -> CalendarWindow:
    return CalendarWindow(start=_dt(start_h), end=_dt(end_h), value=value)


def _window_at(
    start_h: int,
    start_m: int,
    end_h: int,
    end_m: int,
    value: float,
) -> CalendarWindow:
    return CalendarWindow(start=_dt(start_h, start_m), end=_dt(end_h, end_m), value=value)


def _boundaries_at(*hour_minute: tuple[int, int]) -> list[datetime]:
    return [_dt(h, m) for h, m in hour_minute]


# --- fuse_windows_to_boundaries ---


def test_fuse_no_windows() -> None:
    """Fuse no windows."""
    result = fuse_windows_to_boundaries([], _boundaries(8, 9, 10, 11))
    assert result == [None, None, None, None]


def test_fuse_empty_boundaries() -> None:
    """Fuse empty boundaries."""
    result = fuse_windows_to_boundaries([_window(8, 10)], [])
    assert result == []


def test_fuse_single_window_aligned() -> None:
    """Window exactly covers one period."""
    result = fuse_windows_to_boundaries(
        [_window(9, 10, value=5.0)],
        _boundaries(8, 9, 10, 11),
    )
    assert result == [None, 5.0, None, None]


def test_fuse_single_window_mid_period() -> None:
    """Window starts/ends mid-period — snaps to period boundaries."""
    result = fuse_windows_to_boundaries(
        [CalendarWindow(start=_dt(9, 15), end=_dt(9, 45), value=3.0)],
        _boundaries(8, 9, 10, 11),
    )
    # 9:15 floors to boundary[1] (9:00), 9:45 ceils to boundary[2] (10:00)
    assert result == [None, 3.0, None, None]


def test_fuse_spanning_multiple_periods() -> None:
    """Fuse spanning multiple periods."""
    result = fuse_windows_to_boundaries(
        [_window(9, 11, value=7.0)],
        _boundaries(8, 9, 10, 11, 12),
    )
    assert result == [None, 7.0, 7.0, None, None]


def test_fuse_multiple_windows() -> None:
    """Fuse multiple windows."""
    result = fuse_windows_to_boundaries(
        [_window(8, 9, value=1.0), _window(10, 11, value=2.0)],
        _boundaries(8, 9, 10, 11),
    )
    assert result == [1.0, None, 2.0, None]


def test_fuse_window_outside_horizon() -> None:
    """Fuse window outside horizon."""
    result = fuse_windows_to_boundaries(
        [_window(5, 6, value=1.0)],
        _boundaries(8, 9, 10),
    )
    assert result == [None, None, None]


def test_fuse_window_partially_overlaps_start() -> None:
    """Fuse window partially overlaps start."""
    result = fuse_windows_to_boundaries(
        [_window(7, 9, value=4.0)],
        _boundaries(8, 9, 10),
    )
    # Window starts before horizon (floors to 0), ends at boundary[1]
    assert result == [4.0, None, None]


def test_fuse_window_partially_overlaps_end() -> None:
    """Fuse window partially overlaps end."""
    result = fuse_windows_to_boundaries(
        [_window(9, 12, value=4.0)],
        _boundaries(8, 9, 10),
    )
    assert result == [None, 4.0, 4.0]


def test_fuse_overlapping_windows_sums() -> None:
    """Fuse overlapping windows sums values at shared boundaries."""
    result = fuse_windows_to_boundaries(
        [_window(9, 11, value=1.0), _window(10, 12, value=2.0)],
        _boundaries(8, 9, 10, 11, 12),
    )
    assert result == [None, 1.0, 3.0, 2.0, None]


# --- fuse_window_edges_to_boundaries ---


def test_fuse_edge_start_floors() -> None:
    """Start edge places value at floored boundary."""
    result = fuse_window_edges_to_boundaries(
        [CalendarWindow(start=_dt(9, 15), end=_dt(9, 45), value=3.0)],
        _boundaries(8, 9, 10, 11),
        edge="start",
    )
    assert result == [None, 3.0, None, None]


def test_fuse_edge_end_ceils() -> None:
    """End edge places value at ceiled boundary."""
    result = fuse_window_edges_to_boundaries(
        [CalendarWindow(start=_dt(9, 15), end=_dt(9, 45), value=3.0)],
        _boundaries(8, 9, 10, 11),
        edge="end",
    )
    assert result == [None, None, 3.0, None]


def test_fuse_edge_back_to_back_distinct_boundaries() -> None:
    """Back-to-back trips get distinct start and end boundaries."""
    windows = [_window(6, 8, value=5.0), _window(9, 11, value=7.0)]
    boundaries = _boundaries(6, 7, 8, 9, 10, 11, 12)

    starts = fuse_window_edges_to_boundaries(windows, boundaries, edge="start")
    ends = fuse_window_edges_to_boundaries(windows, boundaries, edge="end")

    assert starts == [5.0, None, None, 7.0, None, None, None]
    assert ends == [None, None, 5.0, None, None, 7.0, None]


def test_fuse_edge_same_boundary_sums() -> None:
    """When two windows share an edge boundary, values are summed."""
    windows = [_window(8, 9, value=1.0), _window(8, 9, value=2.0)]
    boundaries = _boundaries(8, 9, 10)

    starts = fuse_window_edges_to_boundaries(windows, boundaries, edge="start")
    assert starts == [3.0, None, None]


def test_fuse_edge_empty_inputs() -> None:
    """Empty windows or boundaries return empty or all-None."""
    assert fuse_window_edges_to_boundaries([], _boundaries(8, 9), edge="start") == [None, None]
    assert fuse_window_edges_to_boundaries([_window(8, 9)], [], edge="end") == []


def test_integration_deferrable_load_signals() -> None:
    """Derive start, end, and active signals for a deferrable load."""
    windows = [_window(9, 11, value=5.0)]
    boundaries = _boundaries(8, 9, 10, 11, 12)

    starts = fuse_window_edges_to_boundaries(windows, boundaries, edge="start")
    ends = fuse_window_edges_to_boundaries(windows, boundaries, edge="end")
    active = fuse_windows_to_boundaries(windows, boundaries)

    assert starts == [None, 5.0, None, None, None]
    assert ends == [None, None, None, 5.0, None]
    assert active == [None, 5.0, 5.0, None, None]


# --- fill_none ---


def test_fill_none_with_zero() -> None:
    """Fill none with zero."""
    assert fill_none([1.0, None, 2.0, None], 0.0) == [1.0, 0.0, 2.0, 0.0]


def test_fill_none_with_one() -> None:
    """Connected-flag pattern: None = connected = 1.0."""
    assert fill_none([None, 0.5, None], 1.0) == [1.0, 0.5, 1.0]


def test_fill_none_empty() -> None:
    """Fill none empty."""
    assert fill_none([], 0.0) == []


def test_fill_none_all_none() -> None:
    """Fill none all none."""
    assert fill_none([None, None, None], 42.0) == [42.0, 42.0, 42.0]


def test_fill_none_no_none() -> None:
    """Fill none no none."""
    assert fill_none([1.0, 2.0, 3.0], 0.0) == [1.0, 2.0, 3.0]


# --- Integration: windows → boundaries → filled ---


def test_integration_ev_availability() -> None:
    """Simulate EV disconnected during a trip, connected otherwise."""
    windows = [_window(9, 11, value=0.0)]  # away = 0.0
    boundaries = _boundaries(6, 7, 8, 9, 10, 11, 12, 13)

    raw = fuse_windows_to_boundaries(windows, boundaries)
    assert raw == [None, None, None, 0.0, 0.0, None, None, None]

    filled = fill_none(raw, 1.0)  # connected = 1.0
    assert filled == [1.0, 1.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0]


def test_integration_energy_demand() -> None:
    """Simulate energy demand during trip windows."""
    windows = [
        _window(9, 10, value=5.0),  # 5 kWh trip
        _window(14, 16, value=12.0),  # 12 kWh trip
    ]
    boundaries = _boundaries(8, 9, 10, 11, 12, 13, 14, 15, 16, 17)

    raw = fuse_windows_to_boundaries(windows, boundaries)
    assert raw == [None, 5.0, None, None, None, None, 12.0, 12.0, None, None]

    filled = fill_none(raw, 0.0)
    assert filled == [0.0, 5.0, 0.0, 0.0, 0.0, 0.0, 12.0, 12.0, 0.0, 0.0]


# --- Parametric fusion scenarios ---


@pytest.mark.parametrize(
    ("case_id", "windows", "boundaries", "expected_start", "expected_end", "expected_active"),
    [
        pytest.param(
            "touching_at_boundary",
            [_window(9, 10, 5.0), _window(10, 11, 7.0)],
            _boundaries(8, 9, 10, 11, 12),
            [None, 5.0, 7.0, None, None],
            [None, None, 5.0, 7.0, None],
            [None, 5.0, 7.0, None, None],
            id="touching_at_boundary",
        ),
        pytest.param(
            "back_to_back_with_gap",
            [_window(6, 8, 5.0), _window(9, 11, 7.0)],
            _boundaries(6, 7, 8, 9, 10, 11, 12),
            [5.0, None, None, 7.0, None, None, None],
            [None, None, 5.0, None, None, 7.0, None],
            [5.0, 5.0, None, 7.0, 7.0, None, None],
            id="back_to_back_with_gap",
        ),
        pytest.param(
            "event_within_one_period",
            [_window_at(9, 15, 9, 45, 5.0)],
            _boundaries(8, 9, 10, 11),
            [None, 5.0, None, None],
            [None, None, 5.0, None],
            [None, 5.0, None, None],
            id="event_within_one_period",
        ),
        pytest.param(
            "two_events_same_period_sums",
            [_window_at(9, 10, 9, 20, 5.0), _window_at(9, 40, 9, 50, 7.0)],
            _boundaries(8, 9, 10, 11),
            [None, 12.0, None, None],
            [None, None, 12.0, None],
            [None, 12.0, None, None],
            id="two_events_same_period_sums",
        ),
        pytest.param(
            "overlapping_events_sum",
            [_window(9, 11, 5.0), _window(10, 12, 7.0)],
            _boundaries(8, 9, 10, 11, 12, 13),
            [None, 5.0, 7.0, None, None, None],
            [None, None, None, 5.0, 7.0, None],
            [None, 5.0, 12.0, 7.0, None, None],
            id="overlapping_events_sum",
        ),
        pytest.param(
            "near_events_adjacent_periods",
            [_window_at(9, 0, 9, 50, 5.0), _window_at(10, 10, 11, 0, 7.0)],
            _boundaries(8, 9, 10, 11, 12),
            [None, 5.0, 7.0, None, None],
            [None, None, 5.0, 7.0, None],
            [None, 5.0, 7.0, None, None],
            id="near_events_adjacent_periods",
        ),
        pytest.param(
            "thirty_min_trips_hourly_boundaries",
            [_window_at(13, 0, 13, 30, 5.0), _window_at(14, 30, 15, 0, 7.0)],
            _boundaries(12, 13, 14, 15, 16),
            [None, 5.0, 7.0, None, None],
            [None, None, 5.0, 7.0, None],
            [None, 5.0, 7.0, None, None],
            id="thirty_min_trips_hourly_boundaries",
        ),
        pytest.param(
            "sub_hour_trips_hourly_boundaries_sums",
            [_window_at(12, 45, 13, 15, 5.0), _window_at(13, 45, 14, 15, 7.0)],
            _boundaries(12, 13, 14, 15),
            [5.0, 7.0, None, None],
            [None, None, 5.0, 7.0],
            [5.0, 12.0, 7.0, None],
            id="sub_hour_trips_hourly_boundaries_sums",
        ),
        pytest.param(
            "sub_hour_trips_30min_boundaries",
            [_window_at(12, 45, 13, 15, 5.0), _window_at(13, 45, 14, 15, 7.0)],
            _boundaries_at((12, 0), (12, 30), (13, 0), (13, 30), (14, 0), (14, 30), (15, 0)),
            [None, 5.0, None, 7.0, None, None, None],
            [None, None, None, 5.0, None, 7.0, None],
            [None, 5.0, 5.0, 7.0, 7.0, None, None],
            id="sub_hour_trips_30min_boundaries",
        ),
        pytest.param(
            "hourly_aligned_no_collision",
            [_window(9, 10, 5.0), _window(11, 12, 7.0)],
            _boundaries(8, 9, 10, 11, 12, 13),
            [None, 5.0, None, 7.0, None, None],
            [None, None, 5.0, None, 7.0, None],
            [None, 5.0, None, 7.0, None, None],
            id="hourly_aligned_no_collision",
        ),
    ],
)
def test_fusion_scenarios(
    case_id: str,
    windows: list[CalendarWindow],
    boundaries: list[datetime],
    expected_start: list[float | None],
    expected_end: list[float | None],
    expected_active: list[float | None],
) -> None:
    """Parametric fusion scenarios for deferrable-load calendar signals."""
    del case_id
    starts = fuse_window_edges_to_boundaries(windows, boundaries, edge="start")
    ends = fuse_window_edges_to_boundaries(windows, boundaries, edge="end")
    active = fuse_windows_to_boundaries(windows, boundaries)

    assert starts == expected_start
    assert ends == expected_end
    assert active == expected_active
