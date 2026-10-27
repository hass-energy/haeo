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
Tests use simple integer timestamps to avoid datetime complexity, except where a forecast steps:
a step moves its earlier point back one ulp, which only survives the cycle arithmetic at realistic
epoch timestamps.
"""

import itertools

import numpy as np
import pytest

from custom_components.haeo.core.data.util.forecast_cycle import normalize_forecast_cycle
from custom_components.haeo.core.data.util.forecast_fuser import fuse_to_boundaries, fuse_to_intervals

_EPOCH = 1_700_000_000.0


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
                (_EPOCH, 100.0),
                (np.nextafter(_EPOCH + 1000.0, -np.inf), 100.0),
                (_EPOCH + 1000.0, 200.0),
                (np.nextafter(_EPOCH + 2000.0, -np.inf), 200.0),
            ],
            [_EPOCH + t for t in (0, 500, 1000, 1500, 2000)],
            # The step at 1000 ends the interval before it at 100 and starts the one after it at 200
            [50.0, 100.0, 200.0, 200.0],
            id="step_function_integration",
        ),
        pytest.param(
            None,
            [(_EPOCH + hour * 3600, float(hour)) for hour in range(25)],
            [_EPOCH + hour * 3600 for hour in (23, 24, 25)],
            # The whole-day forecast reaches 24 at the end of the day, then repeats from 0
            [23.5, 0.5],
            id="cycle_wrap_on_boundary",
        ),
    ],
)
def test_fuse_to_intervals(
    present_value: float | None,
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
            [],
            [0, 1000, 2000, 3000],
            [50.0, 50.0, 50.0, 50.0],
            id="present_only_no_forecast",
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
        pytest.param(
            None,
            [
                (_EPOCH, 100.0),
                (np.nextafter(_EPOCH + 1000.0, -np.inf), 100.0),
                (_EPOCH + 1000.0, 200.0),
                (_EPOCH + 2000.0, 200.0),
            ],
            [_EPOCH + t for t in (0, 500, 1000, 1500)],
            [100.0, 100.0, 200.0, 200.0],
            id="step_on_boundary_samples_later_value",
        ),
        pytest.param(
            None,
            [(_EPOCH + hour * 3600, float(hour)) for hour in range(25)],
            [_EPOCH + hour * 3600 for hour in (23, 24, 25)],
            [23.0, 0.0, 1.0],
            id="cycle_wrap_on_boundary_samples_later_value",
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


def test_fuse_to_boundaries_raises_when_no_data() -> None:
    """Test that missing both forecast_series and present_value raises ValueError."""
    with pytest.raises(ValueError, match="Either forecast_series or present_value must be provided"):
        fuse_to_boundaries(None, [], [0, 1000, 2000])


def _reference_interval_averages(
    present_value: float | None,
    forecast_series: list[tuple[float, float]],
    horizon_times: list[float],
) -> list[float]:
    """Average each interval with a trapezoid over its own boundaries and the block points strictly inside it."""
    # The forecast repeats every cycle, from one cycle before the horizon to past its end
    block, cycle = normalize_forecast_cycle(forecast_series, horizon_times[0])
    repeats = range(-1, int(np.ceil((horizon_times[-1] - horizon_times[0]) / cycle)) + 2)
    times = np.array([time + i * cycle for i in repeats for time, _ in block])
    values = np.array([value for _ in repeats for _, value in block])
    result: list[float] = []
    for start, end in itertools.pairwise(horizon_times):
        inside = (times > start) & (times < end)
        knot_times = np.concatenate([[start], times[inside], [end]])
        knot_values = np.concatenate(
            [[np.interp(start, times, values)], values[inside], [np.interp(end, times, values)]]
        )
        result.append(float(np.trapezoid(knot_values, knot_times) / (end - start)))
    if present_value is not None:
        result[0] = present_value
    return result


def _random_case(seed: int) -> tuple[float | None, list[tuple[float, float]], list[float]]:
    rng = np.random.default_rng(seed)
    widths = rng.choice([60.0, 300.0, 900.0, 1800.0, 3600.0], int(rng.integers(2, 80)))
    horizon = (_EPOCH + np.concatenate([[0.0], np.cumsum(widths)])).tolist()
    times = np.sort(_EPOCH + rng.uniform(-7200.0, 2 * 86400.0, int(rng.integers(1, 60))))
    # Put some points exactly on horizon boundaries
    on_boundary = rng.choice(horizon, min(len(times), 3), replace=False)
    times = np.sort(np.concatenate([times, on_boundary]))
    series = list(zip(times.tolist(), rng.normal(3.0, 2.0, len(times)).tolist(), strict=True))
    return (None if seed % 2 else 1.5), series, horizon


@pytest.mark.parametrize(
    ("present_value", "forecast_series", "horizon_times"),
    [
        pytest.param(
            None,
            [(_EPOCH, 100.0), (np.nextafter(_EPOCH + 1000.0, -np.inf), 100.0), (_EPOCH + 1000.0, 200.0)],
            [_EPOCH + t for t in (0.0, 500.0, 1000.0, 1500.0)],
            id="step_on_boundary",
        ),
        pytest.param(
            None,
            [(_EPOCH, 1.0), (_EPOCH + 1000.0, 1.0), (_EPOCH + 1000.0, 2.0), (_EPOCH + 2000.0, 2.0)],
            [_EPOCH + t for t in (0.0, 500.0, 1000.0, 1500.0, 2000.0)],
            id="duplicate_timestamps_on_boundary",
        ),
        pytest.param(
            None,
            [(_EPOCH + 2000.0, 5.0), (_EPOCH + 2600.0, 8.0)],
            [_EPOCH + t for t in (0.0, 1000.0, 3000.0, 4000.0)],
            id="forecast_starts_inside_horizon",
        ),
        pytest.param(
            2.0,
            [(_EPOCH - 5000.0, 1.0), (_EPOCH + 100.0, 4.0), (_EPOCH + 200.0, 2.0), (_EPOCH + 9000.0, 6.0)],
            [_EPOCH + t for t in (0.0, 300.0, 600.0)],
            id="points_inside_one_interval_and_beyond_horizon",
        ),
        *(pytest.param(*_random_case(seed), id=f"random_{seed}") for seed in range(20)),
    ],
)
def test_fuse_to_intervals_matches_per_interval_trapezoids(
    present_value: float | None,
    forecast_series: list[tuple[float, float]],
    horizon_times: list[float],
) -> None:
    """Interval averages match integrating each interval on its own."""
    expected = _reference_interval_averages(present_value, forecast_series, horizon_times)

    assert fuse_to_intervals(present_value, forecast_series, horizon_times) == pytest.approx(expected, rel=1e-12)


def test_interpolation_context_before_horizon_start() -> None:
    """Test that interpolation at horizon_start uses prior cycle data, not flat extrapolation.

    When normalize_forecast_cycle wraps a forecast, the first block point may be
    well after horizon_start. Without a prior cycle, np.interp flat-extrapolates
    from the first point, giving incorrect values.
    """
    # Solar-like ramp over 24h
    forecast: list[tuple[int, float]] = [
        (0, 0.0),
        (21600, 0.5),
        (43200, 1.0),
        (64800, 0.5),
        (86400, 0.0),
    ]

    # Horizon at t=50000 falls between noon (43200, 1.0) and 6pm (64800, 0.5)
    horizon_start = 50000.0
    expected_value = 1.0 + (50000 - 43200) / (64800 - 43200) * (0.5 - 1.0)

    result = fuse_to_boundaries(None, forecast, [horizon_start, horizon_start + 10000])

    # Without the prior cycle fix, this returns 0.5 (flat extrapolation from first block point)
    assert result[0] == pytest.approx(expected_value, abs=0.01)


def test_whole_day_forecast_ramps_to_its_end_value_before_repeating() -> None:
    """A forecast ending at its start's time of day reaches its last value, then repeats from its first."""
    # Six-hourly points from midnight to the next midnight
    forecast: list[tuple[int, float]] = [(hour * 3600, hour / 6) for hour in range(0, 25, 6)]
    horizon_times = [hour * 3600.0 for hour in (7, 21, 23, 25)]

    result = fuse_to_boundaries(None, forecast, horizon_times)

    assert result == pytest.approx([7 / 6, 3.5, 23 / 6, 1 / 6])
