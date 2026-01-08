"""Unit tests for forecast fusion logic.

The fuser combines present values with forecast data to create horizon-aligned interval values using
the boundary pattern where n+1 timestamps produce n interval values:
- Position 0: Present value (actual current state at t0)
- Position k (k≥1): Interval average over [horizon_times[k-1] → horizon_times[k]]

Tests cover:
- Present value override behavior (0.0 vs actual values)
- Interval averaging via trapezoidal integration
- Edge cases (empty forecasts, constant values, misaligned timestamps)

Cycling behavior (forecast shorter than horizon) is tested in test_forecast_cycle.py.
Tests use simple integer timestamps to avoid datetime complexity.
"""

import numpy as np
import pytest

from custom_components.haeo.data.util.forecast_fuser import fuse_to_boundaries, fuse_to_intervals


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
        pytest.param(
            50.0,
            [
                (0.0, 100.0),
                (np.nextafter(1000.0, -np.inf), 100.0),
                (1000.0, 200.0),
                (np.nextafter(2000.0, -np.inf), 200.0),
            ],
            [0, 500, 1000, 1500, 2000],
            # Interval [0,500]: present value override = 50.0
            # Interval [500,1000]: trapezoidal from 500 to 1000, includes step at boundary
            #   - Most of interval at 100, but includes point at t=1000 with value=200
            #   - Result: ~150 (average of 100 and 200 at the boundary)
            # Interval [1000,1500]: constant at 200
            # Interval [1500,2000]: constant at 200
            [50.0, 150.0, 200.0, 200.0],
            id="step_function_integration",
        ),
    ],
)
def test_fuse_to_intervals(
    present_value: float,
    forecast_series: list[tuple[int, float]],
    horizon_times: list[int],
    expected: list[float],
) -> None:
    """Test fuse_to_intervals with various input configurations using boundary pattern.

    With n+1 boundary timestamps, returns n_periods values where:
    - Position 0: Present value (replaces first interval, not affecting future forecast)
    - Positions 1 to n-1: Interval averages computed from pure forecast data

    This gives n_periods = len(horizon_times) - 1 total values.

    Present value does NOT influence forecast computation - it only replaces the
    first interval result. All subsequent intervals use trapezoidal integration
    of the forecast data without any present_value influence.
    """
    result = fuse_to_intervals(present_value, forecast_series, horizon_times)

    assert result == pytest.approx(expected)


def test_empty_horizon_times() -> None:
    """Test that empty horizon_times returns empty list."""
    result = fuse_to_intervals(42.0, [(0, 100.0)], [])
    assert result == []


def test_neither_forecast_nor_present_value_raises_error() -> None:
    """Test that missing both forecast_series and present_value raises ValueError."""
    with pytest.raises(ValueError, match="Either forecast_series or present_value must be provided"):
        fuse_to_intervals(None, [], [0, 1000, 2000])


# --- Tests for fuse_to_boundaries ---


@pytest.mark.parametrize(
    ("present_value", "forecast_series", "horizon_times", "expected"),
    [
        pytest.param(
            100.0,
            [(1000, 150.0), (2000, 200.0), (3000, 250.0), (4000, 300.0)],
            [0, 1000, 2000, 3000, 4000],
            [100.0, 150.0, 200.0, 250.0, 300.0],
            id="present_overrides_first_boundary",
        ),
        pytest.param(
            0.0,
            [(1000, 150.0), (2000, 200.0), (3000, 250.0), (4000, 300.0)],
            [0, 1000, 2000, 3000, 4000],
            [0.0, 150.0, 200.0, 250.0, 300.0],
            id="zero_present_value",
        ),
        pytest.param(
            100.0,
            [],
            [0, 1000, 2000, 3000, 4000],
            [100.0, 100.0, 100.0, 100.0, 100.0],
            id="only_present_value_no_forecast",
        ),
        pytest.param(
            50.0,
            [(0, 100.0), (1000, 150.0), (2000, 200.0)],
            [0, 500, 1000, 1500, 2000],
            [50.0, 125.0, 150.0, 175.0, 200.0],
            id="interpolation_with_present_override",
        ),
        pytest.param(
            None,
            [(0, 100.0), (1000, 150.0), (2000, 200.0), (3000, 250.0)],
            [0, 1000, 2000, 3000],
            [100.0, 150.0, 200.0, 250.0],
            id="no_present_value_uses_forecast",
        ),
    ],
)
def test_fuse_to_boundaries(
    present_value: float | None,
    forecast_series: list[tuple[int, float]],
    horizon_times: list[int],
    expected: list[float],
) -> None:
    """Test fuse_to_boundaries returns n+1 point-in-time values.

    With n+1 boundary timestamps, returns n+1 values where:
    - Position 0: Present value if provided, else interpolated from forecast
    - Positions 1 to n: Interpolated values at each boundary timestamp
    """
    result = fuse_to_boundaries(present_value, forecast_series, horizon_times)

    assert result == pytest.approx(expected)


def test_fuse_to_boundaries_empty_horizon() -> None:
    """Test that empty horizon_times returns empty list."""
    result = fuse_to_boundaries(42.0, [(0, 100.0)], [])
    assert result == []


def test_fuse_to_boundaries_present_only() -> None:
    """Test boundaries with only present value (no forecast)."""
    result = fuse_to_boundaries(50.0, [], [0, 1000, 2000, 3000])
    assert result == [50.0, 50.0, 50.0, 50.0]


def test_fuse_to_boundaries_raises_when_no_data() -> None:
    """Test that missing both forecast_series and present_value raises ValueError."""
    with pytest.raises(ValueError, match="Either forecast_series or present_value must be provided"):
        fuse_to_boundaries(None, [], [0, 1000, 2000])
