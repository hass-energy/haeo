"""Unit tests for forecast fusion logic.

The fuser combines present values with forecast data to create horizon-aligned interval values using
the fence post pattern where n+1 boundary timestamps produce n interval values:
- Position 0: Present value (actual current state at t0)
- Position k (k≥1): Interval average over [horizon_times[k-1] → horizon_times[k]]

Tests cover:
- Present value override behavior (0.0 vs actual values)
- Interval averaging via trapezoidal integration
- Edge cases (empty forecasts, constant values, misaligned timestamps)

Cycling behavior (forecast shorter than horizon) is tested in test_forecast_cycle.py.
Tests use simple integer timestamps to avoid datetime complexity.
"""

import pytest

from custom_components.haeo.data.util.forecast_fuser import fuse_to_horizon


@pytest.mark.parametrize(
    ("present_value", "forecast_series", "horizon_times", "expected"),
    [
        pytest.param(
            100.0,
            [(1000, 150.0), (2000, 200.0), (3000, 250.0), (4000, 300.0)],
            [0, 1000, 2000, 3000, 4000],
            [100.0, 175.0, 225.0, 275.0],
            id="present_overrides_forecast_at_t0",
        ),
        pytest.param(
            0.0,
            [(1000, 150.0), (2000, 200.0), (3000, 250.0), (4000, 300.0)],
            [0, 1000, 2000, 3000, 4000],
            [0.0, 175.0, 225.0, 275.0],
            id="zero_present_value",
        ),
        pytest.param(
            100.0,
            [],
            [0, 1000, 2000, 3000, 4000],
            [100.0, 100.0, 100.0, 100.0],
            id="only_present_value_no_forecast",
        ),
        pytest.param(
            0.0,
            [],
            [0, 1000, 2000, 3000, 4000],
            [0.0, 0.0, 0.0, 0.0],
            id="zero_present_no_forecast_returns_zeros",
        ),
        pytest.param(
            50.0,
            [(0, 100.0), (1000, 150.0), (2000, 200.0), (3000, 250.0)],
            [0, 1000, 2000, 3000],
            [50.0, 175.0, 225.0],
            id="present_at_t0_overrides_forecast",
        ),
        pytest.param(
            0.0,
            [(0, 100.0), (1800, 150.0), (3600, 200.0), (5400, 250.0), (7200, 300.0), (9000, 350.0)],
            [0, 1800, 3600, 5400, 7200, 9000],
            [0.0, 175.0, 225.0, 275.0, 325.0],
            id="present_zero_with_forecast",
        ),
        pytest.param(
            10.0,
            [(1000, 20.0), (2000, 30.0), (3000, 40.0), (4000, 50.0), (5000, 60.0)],
            [0, 1000, 2000, 3000, 4000, 5000],
            [10.0, 25.0, 35.0, 45.0, 55.0],
            id="complete_forecast_coverage",
        ),
        pytest.param(
            5.0,
            [(1000, 15.0), (2000, 20.0), (3000, 25.0)],
            [0, 1000, 2000, 3000, 4000],
            [5.0, 17.5, 22.5, 24.940758293838865],
            id="forecast_cycles_beyond_range",
        ),
        pytest.param(
            42.0,
            [(0, 84.0), (1000, 84.0), (2000, 84.0)],
            [0, 1000, 2000],
            [42.0, 84.0],
            id="present_overrides_constant_forecast",
        ),
        pytest.param(
            30.0,
            [(0, 100.0), (2000, 200.0), (4000, 300.0)],
            [0, 500, 1500, 2500, 3500],  # Horizon boundaries don't align with forecast points
            [30.0, 150.0, 200.0, 250.0],  # present@0, then trapezoidal averages from pure forecast
            id="interpolation_between_forecast_points",
        ),
        pytest.param(
            25.0,
            [(-1000, 50.0), (1000, 150.0), (3000, 250.0)],
            [0, 1000, 2000, 3000],  # Forecast straddles t0 (starts before horizon)
            [25.0, 175.0, 225.0],  # Present@0, then pure forecast averages
            id="forecast_straddles_present_time",
        ),
        pytest.param(
            50.0,
            [(500, 100.0), (1500, 200.0), (2500, 300.0)],
            [0, 1000, 2000, 3000],  # Horizon starts before first forecast point
            [50.0, 200.0, 287.20379146919424],  # present@0, then pure forecast averages
            id="horizon_starts_before_forecast",
        ),
        pytest.param(
            10.0,
            [(0, 100.0), (3000, 400.0)],  # Sparse forecast requiring interpolation
            [0, 1000, 2000, 3000, 4000],  # Multiple intervals between forecast points
            [10.0, 250.0, 350.0, 398.2014388489209],  # present@0, then pure forecast averages
            id="sparse_forecast_multiple_interpolations",
        ),
        pytest.param(
            15.0,
            [(-500, 30.0), (500, 60.0), (1500, 90.0)],  # Forecast before and after t0
            [0, 1000, 2000],  # Check present value replacement works with straddling forecast
            [15.0, 86.1611374407583],  # present@0 replaces first interval, then pure forecast average
            id="forecast_before_and_after_present_override",
        ),
    ],
)
def test_fuse_to_horizon(
    present_value: float,
    forecast_series: list[tuple[int, float]],
    horizon_times: list[int],
    expected: list[float],
) -> None:
    """Test fuse_to_horizon with various input configurations using fence post pattern.

    With n+1 boundary timestamps, returns n_periods values where:
    - Position 0: Present value (replaces first interval, not affecting future forecast)
    - Positions 1 to n-1: Interval averages computed from pure forecast data

    This gives n_periods = len(horizon_times) - 1 total values.

    Present value does NOT influence forecast computation - it only replaces the
    first interval result. All subsequent intervals use trapezoidal integration
    of the forecast data without any present_value influence.
    """
    result = fuse_to_horizon(present_value, forecast_series, horizon_times)

    assert result == pytest.approx(expected)
