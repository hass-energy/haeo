"""Unit tests for time series fusion functions."""

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.haeo.data.loader.fusion import fuse_to_horizon


def test_fuse_to_horizon_separates_present_and_forecast() -> None:
    """Fuse to horizon correctly separates present values from forecast values."""
    start = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    horizon_times = [int((start + timedelta(hours=h)).timestamp()) for h in range(4)]

    # Present value and future forecast
    present_value = 100.0
    forecast_series = [
        (int((start + timedelta(hours=1)).timestamp()), 150.0),
        (int((start + timedelta(hours=2)).timestamp()), 200.0),
    ]

    result = fuse_to_horizon(present_value, forecast_series, horizon_times)

    assert len(result) == 4
    # Present value is added to start of forecast
    # Values are interpolated from the forecast
    assert result[0] == pytest.approx(100.0)
    assert result[1] == pytest.approx(150.0)
    assert result[2] == pytest.approx(200.0)
    # Beyond forecast range, uses daily cycle pattern
    assert result[3] == pytest.approx(150.0)  # Cycles back within the 1-hour range


def test_fuse_to_horizon_handles_no_present_value() -> None:
    """Fuse to horizon works when there is no present value."""
    start = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    horizon_times = [int((start + timedelta(hours=h)).timestamp()) for h in range(3)]

    # Only forecast values
    present_value = 0.0
    forecast_series = [
        (int((start + timedelta(hours=1)).timestamp()), 150.0),
        (int((start + timedelta(hours=2)).timestamp()), 200.0),
    ]

    result = fuse_to_horizon(present_value, forecast_series, horizon_times)

    assert len(result) == 3
    # All values should come from forecast interpolation
    assert result[1] == pytest.approx(150.0)
    assert result[2] == pytest.approx(200.0)


def test_fuse_to_horizon_handles_only_present_value() -> None:
    """Fuse to horizon works when there is only a present value."""
    start = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    horizon_times = [int((start + timedelta(hours=h)).timestamp()) for h in range(24)]

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
    horizon_times = [int((start + timedelta(minutes=m)).timestamp()) for m in [0, 30, 60, 90]]

    # Forecast from hour 0 to hour 1
    present_value = 0.0
    forecast_series = [
        (int(start.timestamp()), 100.0),
        (int((start + timedelta(hours=1)).timestamp()), 200.0),
    ]

    result = fuse_to_horizon(present_value, forecast_series, horizon_times)

    assert len(result) == 4
    assert result[0] == pytest.approx(100.0)  # At start
    assert result[1] == pytest.approx(150.0)  # Halfway interpolated
    assert result[2] == pytest.approx(200.0)  # At end
    # Beyond range (90 minutes), cycles back: 90 minutes % 60 minutes = 30 minutes
    assert result[3] == pytest.approx(150.0)


def test_fuse_to_horizon_extrapolates_beyond_forecast() -> None:
    """Fuse to horizon extrapolates by repeating daily pattern."""
    start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    # Create a 48-hour horizon
    horizon_times = [int((start + timedelta(hours=h)).timestamp()) for h in range(48)]

    # Forecast covering first 25 hours (to ensure coverage >= 24h for daily cycling)
    present_value = 0.0
    forecast_series = [(int((start + timedelta(hours=h)).timestamp()), float(h * 10)) for h in range(25)]

    result = fuse_to_horizon(present_value, forecast_series, horizon_times)

    assert len(result) == 48
    # First 25 hours should match the forecast
    for i in range(25):
        assert result[i] == pytest.approx(float(i * 10))

    # After hour 24, it cycles with 24-hour period
    # The algorithm: sample_ts = min_ts + (sample_ts - min_ts) % cycle_seconds
    # Where cycle_seconds = (coverage // _SECONDS_PER_DAY) * _SECONDS_PER_DAY = 24h
    # For hour 25: (25h - 0h) % 24h = 1h
    # For hour 26: (26h - 0h) % 24h = 2h, etc.
    for i in range(25, 48):
        expected_hour = i % 24  # Cycle back within 24-hour range
        assert result[i] == pytest.approx(float(expected_hour * 10))


def test_fuse_to_horizon_preserves_cycle_from_raw_data_before_current_time() -> None:
    """Fuse to horizon repeats using cycle detected from raw data prior to truncation."""

    base = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp())
    forecast_series = [
        (base + 0, 10.0),
        (base + 3600, 20.0),
        (base + 7200, 10.0),
        (base + 10800, 20.0),
    ]

    horizon_times = [base + 10800, base + 14400, base + 18000, base + 21600]

    result = fuse_to_horizon(
        0.0,
        forecast_series,
        horizon_times,
        current_time=horizon_times[0],
    )

    # The coverage spans three hours and the repeat cycle is derived from that window,
    # so we expect the sequence to follow the raw pattern before truncation rather than
    # collapsing to a constant tail value.
    assert result == pytest.approx([20.0, 20.0, 10.0, 10.0])


def test_fuse_to_horizon_chooses_shortest_available_cycle() -> None:
    """Fuse to horizon repeats using the shortest detectable interval."""

    start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    horizon_times = [int((start + timedelta(minutes=m)).timestamp()) for m in range(0, 180, 30)]

    present_value = 0.0
    forecast_series = [
        (int(start.timestamp()), 10.0),
        (int((start + timedelta(minutes=30)).timestamp()), 20.0),
        (int((start + timedelta(minutes=60)).timestamp()), 40.0),
    ]

    result = fuse_to_horizon(present_value, forecast_series, horizon_times)

    assert result[:3] == pytest.approx([10.0, 20.0, 40.0])
    # After 60 minutes we wrap on the 60 minute coverage cycle: 90 -> 20, 120 -> 10, 150 -> 20
    assert result[3:] == pytest.approx([20.0, 10.0, 20.0])


def test_fuse_to_horizon_falls_back_to_final_value_without_cycle() -> None:
    """Fuse to horizon uses final forecast value when no repeat period is available."""

    start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    horizon_times = [int((start + timedelta(minutes=m)).timestamp()) for m in range(0, 90, 30)]

    present_value = 5.0
    forecast_series = [
        (int((start + timedelta(minutes=15)).timestamp()), 15.0),
    ]

    result = fuse_to_horizon(present_value, forecast_series, horizon_times)

    assert result[:2] == pytest.approx([5.0, 15.0])
    # Beyond available data there is no cycle, so use last forecast value
    assert result[-1] == pytest.approx(15.0)


def test_fuse_to_horizon_returns_zeros_when_no_data() -> None:
    """Fuse to horizon should emit zeros when both present and forecast data are absent."""

    start = datetime(2024, 1, 1, tzinfo=UTC)
    horizon_times = [int((start + timedelta(hours=h)).timestamp()) for h in range(6)]

    result = fuse_to_horizon(0.0, [], horizon_times)

    assert result == [0.0] * len(horizon_times)


def test_fuse_to_horizon_repeats_single_forecast_value() -> None:
    """Fuse to horizon should repeat a single forecast value across the horizon."""

    timestamp = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp())
    horizon_times = [timestamp + index * 3600 for index in range(4)]

    result = fuse_to_horizon(0.0, [(timestamp, 7.5)], horizon_times)

    assert result == [7.5] * len(horizon_times)
