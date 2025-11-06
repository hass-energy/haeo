"""Unit tests for time series fusion functions."""

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.haeo.data.loader.fusion import combine_sensor_payloads, fuse_to_horizon


def test_combine_sensor_payloads_interpolates_and_sums() -> None:
    """Combine sensor payloads interpolates each forecast and sums at unique timestamps."""
    payloads = {
        "sensor.a": [(0, 1.0), (3600, 2.0)],
        "sensor.b": [(0, 0.5), (7200, 4.0)],
    }

    present_value, forecast_series = combine_sensor_payloads(payloads)

    assert present_value == 0.0
    assert len(forecast_series) == 3
    assert forecast_series[0] == (0, pytest.approx(1.5))
    assert forecast_series[1][0] == 3600
    assert forecast_series[2] == (7200, pytest.approx(4.0))


def test_combine_sensor_payloads_handles_non_overlapping_ranges() -> None:
    """Combine sensor payloads correctly handles forecasts with no overlap."""
    payloads = {
        "sensor.a": [(0, 10.0), (1000, 20.0)],
        "sensor.b": [(2000, 5.0), (3000, 15.0)],
    }

    present_value, forecast_series = combine_sensor_payloads(payloads)

    # Should have all 4 unique timestamps
    assert present_value == 0.0
    assert len(forecast_series) == 4
    timestamps = [ts for ts, _ in forecast_series]
    assert timestamps == [0, 1000, 2000, 3000]

    # At t=0 and t=1000, only sensor.a contributes
    assert forecast_series[0] == (0, pytest.approx(10.0))
    assert forecast_series[1] == (1000, pytest.approx(20.0))

    # At t=2000 and t=3000, only sensor.b contributes
    assert forecast_series[2] == (2000, pytest.approx(5.0))
    assert forecast_series[3] == (3000, pytest.approx(15.0))


def test_combine_sensor_payloads_handles_single_sensor() -> None:
    """Combine sensor payloads works with a single sensor."""
    payloads = {
        "sensor.a": [(0, 1.0), (3600, 2.0), (7200, 3.0)],
    }

    present_value, forecast_series = combine_sensor_payloads(payloads)

    assert present_value == 0.0
    assert len(forecast_series) == 3
    assert forecast_series == [(0, 1.0), (3600, 2.0), (7200, 3.0)]


def test_combine_sensor_payloads_interpolates_at_intermediate_points() -> None:
    """Combine sensor payloads correctly interpolates between points."""
    payloads = {
        "sensor.a": [(0, 0.0), (2000, 10.0)],
        "sensor.b": [(1000, 5.0)],
    }

    present_value, forecast_series = combine_sensor_payloads(payloads)

    # Should have all 3 unique timestamps
    assert present_value == 0.0
    assert len(forecast_series) == 3
    timestamps = [ts for ts, _ in forecast_series]
    assert timestamps == [0, 1000, 2000]

    # At t=0, only sensor.a = 0.0, sensor.b = 0.0 (outside range)
    assert forecast_series[0] == (0, pytest.approx(0.0))

    # At t=1000, sensor.a = 5.0 (interpolated), sensor.b = 5.0
    assert forecast_series[1] == (1000, pytest.approx(10.0))

    # At t=2000, sensor.a = 10.0, sensor.b = 0.0 (outside range)
    assert forecast_series[2] == (2000, pytest.approx(10.0))


def test_combine_sensor_payloads_separates_floats_and_forecasts() -> None:
    """Combine sensor payloads correctly separates simple floats from forecast series."""
    payloads = {
        "sensor.live": 100.0,
        "sensor.live2": 50.0,
        "sensor.forecast": [(0, 10.0), (3600, 20.0)],
    }

    present_value, forecast_series = combine_sensor_payloads(payloads)

    assert present_value == pytest.approx(150.0)
    assert len(forecast_series) == 2
    assert forecast_series == [(0, 10.0), (3600, 20.0)]


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
