"""Tests for forecast payload combination utilities."""

import numpy as np
import pytest

from custom_components.haeo.core.data.util.forecast_combiner import combine_sensor_payloads

type Payloads = dict[str, float | list[tuple[float, float]]]


@pytest.mark.parametrize(
    ("payloads", "expected_present", "expected_forecast"),
    [
        pytest.param(
            {
                "sensor.a": [(0, 1.0), (3600, 2.0)],
                "sensor.b": [(0, 0.5), (7200, 4.0)],
            },
            None,
            [(0, 1.5), (3600, 4.25), (7200, 4.0)],
            id="interpolate_and_sum_two_forecasts",
        ),
        pytest.param(
            {
                "sensor.a": [(0, 10.0), (1000, 20.0)],
                "sensor.b": [(2000, 5.0), (3000, 15.0)],
            },
            None,
            [(0, 10.0), (1000, 20.0), (2000, 5.0), (3000, 15.0)],
            id="non_overlapping_forecast_ranges",
        ),
        pytest.param(
            {
                "sensor.a": [(0, 1.0), (3600, 2.0), (7200, 3.0)],
            },
            None,
            [(0, 1.0), (3600, 2.0), (7200, 3.0)],
            id="single_forecast_sensor",
        ),
        pytest.param(
            {
                "sensor.a": [(0, 0.0), (2000, 10.0)],
                "sensor.b": [(1000, 5.0)],
            },
            None,
            [(0, 0.0), (1000, 10.0), (2000, 10.0)],
            id="interpolate_at_intermediate_points",
        ),
        pytest.param(
            {
                "sensor.live": 100.0,
                "sensor.live2": 50.0,
                "sensor.forecast": [(0, 10.0), (3600, 20.0)],
            },
            150.0,
            [(0, 10.0), (3600, 20.0)],
            id="separate_present_and_forecast_values",
        ),
        pytest.param(
            {
                "sensor.live1": 25.0,
                "sensor.live2": 75.0,
            },
            100.0,
            [],
            id="only_present_values",
        ),
        pytest.param(
            {
                "sensor.live": 42.0,
            },
            42.0,
            [],
            id="single_present_value",
        ),
        pytest.param(
            {},
            None,
            [],
            id="empty_payloads",
        ),
        pytest.param(
            {
                "sensor.a": [(0, 100.0), (1000, 200.0)],
                "sensor.b": [(500, 50.0)],
                "sensor.live": 10.0,
            },
            10.0,
            [(0, 100.0), (500, 200.0), (1000, 200.0)],
            id="mixed_present_and_multiple_forecasts",
        ),
        pytest.param(
            {
                "sensor.step": [
                    (0.0, 10.0),
                    (np.nextafter(1000.0, -np.inf), 10.0),
                    (1000.0, 20.0),
                    (np.nextafter(2000.0, -np.inf), 20.0),
                ],
            },
            None,
            [
                (0.0, 10.0),
                (np.nextafter(1000.0, -np.inf), 10.0),
                (1000.0, 20.0),
                (np.nextafter(2000.0, -np.inf), 20.0),
            ],
            id="step_function_preserved",
        ),
        pytest.param(
            {
                "sensor.step1": [
                    (0.0, 10.0),
                    (np.nextafter(1000.0, -np.inf), 10.0),
                    (1000.0, 20.0),
                    (np.nextafter(2000.0, -np.inf), 20.0),
                ],
                "sensor.step2": [
                    (0.0, 5.0),
                    (np.nextafter(1000.0, -np.inf), 5.0),
                    (1000.0, 15.0),
                    (np.nextafter(2000.0, -np.inf), 15.0),
                ],
            },
            None,
            [
                (0.0, 15.0),
                (np.nextafter(1000.0, -np.inf), 15.0),
                (1000.0, 35.0),
                (np.nextafter(2000.0, -np.inf), 35.0),
            ],
            id="step_functions_combine",
        ),
        pytest.param(
            {
                "sensor.step_with_gap": [
                    # Previous window ends at 999.999...
                    (np.nextafter(1000.0, -np.inf), 0.06),
                    # Gap from 1000.0 to 1001.0 (1 second)
                    # Next window starts at 1001.0
                    (1001.0, 0.04),
                    (np.nextafter(2001.0, -np.inf), 0.04),
                ],
            },
            None,
            [
                (np.nextafter(1000.0, -np.inf), 0.06),
                (1001.0, 0.04),
                (np.nextafter(2001.0, -np.inf), 0.04),
            ],
            id="step_function_with_gap_preserved",
        ),
    ],
)
def test_combine_sensor_payloads(
    payloads: Payloads,
    expected_present: float | None,
    expected_forecast: list[tuple[float, float]],
) -> None:
    """Test combining sensor payloads with various input configurations."""
    present_value, forecast_series = combine_sensor_payloads(payloads)

    if expected_present is None:
        assert present_value is None
    else:
        assert present_value == pytest.approx(expected_present)

    assert len(forecast_series) == len(expected_forecast)
    for (actual_ts, actual_val), (expected_ts, expected_val) in zip(forecast_series, expected_forecast, strict=True):
        assert actual_ts == expected_ts
        assert actual_val == pytest.approx(expected_val)
