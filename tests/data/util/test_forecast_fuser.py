"""Unit tests for forecast fusion logic.

These tests focus on the fuser's core responsibilities:
- Placing present value at position 0
- Computing interval averages using trapezoidal integration
- Handling edge cases (empty data, missing values)

Cycling behavior is tested comprehensively in test_forecast_cycle.py.
Tests here use forecast data that covers the entire horizon to avoid cycling complexity.
"""

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.haeo.data.util.forecast_fuser import fuse_to_horizon


def test_fuse_to_horizon_separates_present_and_forecast() -> None:
    """Fuse to horizon correctly separates present values from forecast values."""
    start = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    # Use 4 boundary timestamps (3 intervals): [t0, t1, t2, t3]
    # This creates 3 intervals: [t0→t1], [t1→t2], [t2→t3]
    horizon_times = [int((start + timedelta(hours=h)).timestamp()) for h in range(4)]

    # Present value and future forecast
    present_value = 100.0
    forecast_series = [
        (int((start + timedelta(hours=1)).timestamp()), 150.0),
        (int((start + timedelta(hours=2)).timestamp()), 200.0),
        (int((start + timedelta(hours=3)).timestamp()), 250.0),
    ]

    result = fuse_to_horizon(present_value, forecast_series, horizon_times)

    assert len(result) == 3
    # Position 0: Present value at t0
    assert result[0] == pytest.approx(100.0)
    # Position 1: Interval average over [t0 → t1], linear from 100 to 150
    assert result[1] == pytest.approx(125.0)
    # Position 2: Interval average over [t1 → t2], linear from 150 to 200
    assert result[2] == pytest.approx(175.0)


def test_fuse_to_horizon_handles_no_present_value() -> None:
    """Fuse to horizon works when there is no present value."""
    start = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    # 4 boundary timestamps for 3 intervals
    horizon_times = [int((start + timedelta(hours=h)).timestamp()) for h in range(4)]

    # Only forecast values
    present_value = 0.0
    forecast_series = [
        (int((start + timedelta(hours=1)).timestamp()), 150.0),
        (int((start + timedelta(hours=2)).timestamp()), 200.0),
        (int((start + timedelta(hours=3)).timestamp()), 250.0),
    ]

    result = fuse_to_horizon(present_value, forecast_series, horizon_times)

    assert len(result) == 3
    # Position 0: Present value (0.0)
    assert result[0] == pytest.approx(0.0)
    # Position 1: Interval average over [t0 → t1], linear from 0 to 150
    assert result[1] == pytest.approx(75.0)
    # Position 2: Interval average over [t1 → t2], linear from 150 to 200
    assert result[2] == pytest.approx(175.0)


def test_fuse_to_horizon_handles_only_present_value() -> None:
    """Fuse to horizon works when there is only a present value."""
    start = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    # 25 boundary timestamps for 24 intervals
    horizon_times = [int((start + timedelta(hours=h)).timestamp()) for h in range(25)]

    # Only present value, no forecast
    present_value = 100.0
    forecast_series: list[tuple[int, float]] = []

    result = fuse_to_horizon(present_value, forecast_series, horizon_times)

    assert len(result) == 24
    # All values should be the present value repeated
    for value in result:
        assert value == pytest.approx(100.0)


def test_fuse_to_horizon_interpolates_within_forecast_range() -> None:
    """Fuse to horizon correctly interpolates within the forecast range."""
    start = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    # 5 boundary timestamps for 4 intervals
    horizon_times = [int((start + timedelta(minutes=m)).timestamp()) for m in [0, 30, 60, 90, 120]]

    # Forecast covering entire horizon to avoid cycling
    present_value = 0.0
    forecast_series = [
        (int(start.timestamp()), 100.0),
        (int((start + timedelta(minutes=30)).timestamp()), 150.0),
        (int((start + timedelta(minutes=60)).timestamp()), 200.0),
        (int((start + timedelta(minutes=90)).timestamp()), 250.0),
        (int((start + timedelta(minutes=120)).timestamp()), 300.0),
    ]

    result = fuse_to_horizon(present_value, forecast_series, horizon_times)

    assert len(result) == 4
    # Position 0: Present value (0.0, overrides forecast)
    assert result[0] == pytest.approx(0.0)
    # Position 1: Interval average over [0 → 30min], linear from 0 to 150
    assert result[1] == pytest.approx(75.0)
    # Position 2: Interval average over [30 → 60min], linear from 150 to 200
    assert result[2] == pytest.approx(175.0)
    # Position 3: Interval average over [60 → 90min], linear from 200 to 250
    assert result[3] == pytest.approx(225.0)


def test_fuse_to_horizon_with_cycling() -> None:
    """Fuse to horizon handles horizons beyond forecast range via cycling."""
    start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    # 9 boundary timestamps for 8 intervals
    horizon_times = [int((start + timedelta(hours=h)).timestamp()) for h in range(9)]

    # Forecast covering first 6 hours
    present_value = 0.0
    forecast_series = [(int((start + timedelta(hours=h)).timestamp()), float(h * 10)) for h in range(7)]

    result = fuse_to_horizon(present_value, forecast_series, horizon_times)

    # Verify correct length and present value at position 0
    assert len(result) == 8
    assert result[0] == pytest.approx(0.0)
    # Remaining values are produced by cycling logic (tested in test_forecast_cycle.py)
    assert all(isinstance(v, float) for v in result)


def test_fuse_to_horizon_with_single_forecast_point() -> None:
    """Fuse to horizon handles a single forecast point."""
    start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    # 4 boundary timestamps for 3 intervals
    horizon_times = [int((start + timedelta(hours=h)).timestamp()) for h in range(4)]

    present_value = 5.0
    forecast_series = [
        (int((start + timedelta(hours=1)).timestamp()), 15.0),
        (int((start + timedelta(hours=2)).timestamp()), 20.0),
    ]

    result = fuse_to_horizon(present_value, forecast_series, horizon_times)

    assert len(result) == 3
    # Position 0: Present value
    assert result[0] == pytest.approx(5.0)
    # Position 1: Interval average [0 → 1hr], linear from 5 to 15
    assert result[1] == pytest.approx(10.0)
    # Position 2: Beyond forecast range, handled by cycling
    assert isinstance(result[2], float)


def test_fuse_to_horizon_returns_zeros_when_no_data() -> None:
    """Fuse to horizon should emit zeros when both present and forecast data are absent."""

    start = datetime(2024, 1, 1, tzinfo=UTC)
    # 7 boundary timestamps for 6 intervals
    horizon_times = [int((start + timedelta(hours=h)).timestamp()) for h in range(7)]

    result = fuse_to_horizon(0.0, [], horizon_times)

    assert result == [0.0] * 6  # n_periods = 6 intervals


def test_fuse_to_horizon_with_forecast_covering_full_horizon() -> None:
    """Fuse to horizon produces accurate interval averages when forecast covers entire horizon."""
    timestamp = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp())
    # 5 boundary timestamps for 4 intervals
    horizon_times = [timestamp + index * 3600 for index in range(5)]

    # Forecast covering entire horizon
    present_value = 0.0
    forecast_series = [
        (timestamp, 10.0),
        (timestamp + 3600, 20.0),
        (timestamp + 7200, 30.0),
        (timestamp + 10800, 40.0),
        (timestamp + 14400, 50.0),
    ]

    result = fuse_to_horizon(present_value, forecast_series, horizon_times)

    # Position 0: Present value (overrides forecast)
    assert result[0] == pytest.approx(0.0)
    # Position 1: Interval average [t0 → t1], linear from 0 to 20
    assert result[1] == pytest.approx(10.0)
    # Position 2: Interval average [t1 → t2], linear from 20 to 30
    assert result[2] == pytest.approx(25.0)
    # Position 3: Interval average [t2 → t3], linear from 30 to 40
    assert result[3] == pytest.approx(35.0)
