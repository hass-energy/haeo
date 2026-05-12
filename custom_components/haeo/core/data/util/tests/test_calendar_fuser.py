"""Tests for calendar window fusion to horizon boundaries."""

from datetime import UTC, datetime

from custom_components.haeo.core.data.loader.calendar import CalendarWindow
from custom_components.haeo.core.data.util.calendar_fuser import fill_none, fuse_windows_to_boundaries


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2025, 1, 1, hour, minute, tzinfo=UTC)


def _boundaries(*hours: int) -> list[datetime]:
    return [_dt(h) for h in hours]


def _window(start_h: int, end_h: int, value: float = 1.0) -> CalendarWindow:
    return CalendarWindow(start=_dt(start_h), end=_dt(end_h), value=value)


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


def test_fuse_overlapping_windows_last_wins() -> None:
    """Fuse overlapping windows last wins."""
    result = fuse_windows_to_boundaries(
        [_window(9, 11, value=1.0), _window(10, 12, value=2.0)],
        _boundaries(8, 9, 10, 11, 12),
    )
    # Period 10-11 overlapped by both; second window (value=2.0) wins
    assert result == [None, 1.0, 2.0, 2.0, None]


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
