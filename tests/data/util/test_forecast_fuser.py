"""Unit tests for forecast fusion logic.

The fuser combines present values with forecast data to create horizon-aligned interval values:
- Position 0: Present value (actual current state), or first interval average if None
- Position k (k≥1): Interval average over [horizon_times[k] → horizon_times[k+1]]

Tests cover:
- Present value override behavior (None vs 0.0 vs actual values)
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
            [(1000, 150.0), (2000, 200.0), (3000, 250.0)],
            [0, 1000, 2000, 3000],
            [100.0, 175.0, 225.0],
            id="present_overrides_forecast_at_t0",
        ),
        pytest.param(
            None,
            [(0, 150.0), (1000, 200.0), (2000, 250.0)],
            [0, 1000, 2000],
            [175.0, 225.0],
            id="none_present_uses_forecast_intervals",
        ),
        pytest.param(
            0.0,
            [(1000, 150.0), (2000, 200.0), (3000, 250.0)],
            [0, 1000, 2000, 3000],
            [0.0, 175.0, 225.0],
            id="zero_present_value",
        ),
        pytest.param(
            100.0,
            [],
            [0, 1000, 2000, 3000],
            [100.0, 100.0, 100.0],
            id="only_present_value_no_forecast",
        ),
        pytest.param(
            None,
            [],
            [0, 1000, 2000, 3000],
            [0.0, 0.0, 0.0],
            id="none_present_no_forecast_returns_zeros",
        ),
        pytest.param(
            50.0,
            [(0, 100.0), (1000, 150.0), (2000, 200.0)],
            [0, 1000, 2000],
            [50.0, 175.0],
            id="present_at_t0_overrides_forecast",
        ),
        pytest.param(
            0.0,
            [(0, 100.0), (1800, 150.0), (3600, 200.0), (5400, 250.0), (7200, 300.0)],
            [0, 1800, 3600, 5400, 7200],
            [0.0, 175.0, 225.0, 275.0],
            id="present_zero_with_forecast",
        ),
        pytest.param(
            10.0,
            [(1000, 20.0), (2000, 30.0), (3000, 40.0), (4000, 50.0)],
            [0, 1000, 2000, 3000, 4000],
            [10.0, 25.0, 35.0, 45.0],
            id="complete_forecast_coverage",
        ),
        pytest.param(
            5.0,
            [(1000, 15.0), (2000, 20.0)],
            [0, 1000, 2000, 3000],
            [5.0, 17.5, 19.911137440758292],
            id="forecast_cycles_beyond_range",
        ),
        pytest.param(
            None,
            [(1000, 100.0), (2000, 200.0)],
            [0, 1000, 2000],
            [100.0, 150.0],
            id="none_present_with_forecast",
        ),
        pytest.param(
            42.0,
            [(0, 84.0), (1000, 84.0)],
            [0, 1000],
            [42.0],
            id="present_overrides_constant_forecast",
        ),
        pytest.param(
            None,
            [(0, 100.0), (1000, 100.0), (2000, 100.0)],
            [0, 1000, 2000],
            [100.0, 100.0],
            id="none_present_constant_forecast",
        ),
    ],
)
def test_fuse_to_horizon(
    present_value: float | None,
    forecast_series: list[tuple[int, float]],
    horizon_times: list[int],
    expected: list[float],
) -> None:
    """Test fuse_to_horizon with various input configurations.

    When present_value is provided:
    - Position 0 contains the present value (actual current state at t0)
    - Positions 1+ contain interval averages starting from the next boundary

    When present_value is None:
    - All positions contain interval averages computed from forecast data

    All interval averages use trapezoidal integration.
    """
    result = fuse_to_horizon(present_value, forecast_series, horizon_times)

    assert len(result) == len(expected)
    for actual, exp in zip(result, expected, strict=True):
        assert actual == pytest.approx(exp)
