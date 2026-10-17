"""Tests for combining sensor payloads into one horizon-aligned series."""

import pytest

from custom_components.haeo.core.data.util.forecast_combiner import fuse_sensor_payloads, split_sensor_payloads

HOUR = 3600.0
DAY = 24 * HOUR

type Payloads = dict[str, float | list[tuple[float, float]]]


@pytest.mark.parametrize(
    ("payloads", "expected_present", "expected_count"),
    [
        pytest.param({"sensor.a": 1.0, "sensor.b": 2.5}, 3.5, 0, id="present_values_sum"),
        pytest.param({"sensor.a": [(0.0, 1.0)], "sensor.b": [(0.0, 2.0)]}, None, 2, id="forecasts_kept_apart"),
        pytest.param({"sensor.a": 1.0, "sensor.b": [(0.0, 2.0)]}, 1.0, 1, id="mixed"),
        pytest.param({}, None, 0, id="empty"),
        pytest.param({"sensor.a": [(0.0, 2.0)], "calendar.b": []}, None, 1, id="forecast_with_no_points_adds_nothing"),
    ],
)
def test_split_sensor_payloads(payloads: Payloads, expected_present: float | None, expected_count: int) -> None:
    """Present values sum, and each forecast is kept on its own."""
    present_value, forecast_series = split_sensor_payloads(payloads)

    assert present_value == expected_present
    assert len(forecast_series) == expected_count


def test_short_forecast_repeats_beside_one_covering_the_horizon() -> None:
    """A one-day forecast repeats to fill the horizon even when another forecast covers it all."""
    times = [0.0, DAY, 2 * DAY]
    one_day = [(0.0, 1.0), (DAY - HOUR, 1.0)]
    two_days = [(0.0, 10.0), (2 * DAY, 10.0)]

    assert fuse_sensor_payloads(None, [one_day, two_days], times, boundaries=False) == pytest.approx([11.0, 11.0])


def test_partial_forecasts_join_before_repeating() -> None:
    """Forecasts for consecutive windows join into one rather than each repeating into the other's window."""
    times = [0.0, DAY, 2 * DAY]
    today = [(0.0, 1.0), (DAY - HOUR, 1.0)]
    tomorrow = [(DAY, 3.0), (2 * DAY - HOUR, 3.0)]

    result = fuse_sensor_payloads(None, [today, tomorrow], times, boundaries=False)

    assert result[0] == pytest.approx(1.0, abs=0.1)
    assert result[1] == pytest.approx(3.0, abs=0.1)


def test_forecasts_sum_after_fusing() -> None:
    """Forecasts on different timestamps sum period by period."""
    times = [0.0, HOUR, 2 * HOUR]
    a = [(0.0, 1.0), (DAY - HOUR, 1.0)]
    b = [(0.0, 2.0), (2 * HOUR, 4.0), (DAY - HOUR, 4.0)]

    assert fuse_sensor_payloads(None, [a, b], times, boundaries=False) == pytest.approx([3.5, 4.5])


@pytest.mark.parametrize(
    ("boundaries", "expected"),
    [
        pytest.param(False, [7.0, 2.0], id="first_interval"),
        pytest.param(True, [7.0, 2.0, 2.0], id="first_boundary"),
    ],
)
def test_present_value_is_the_value_for_now(*, boundaries: bool, expected: list[float]) -> None:
    """Beside a forecast, the present value replaces only the first interval or boundary."""
    times = [0.0, HOUR, 2 * HOUR]

    result = fuse_sensor_payloads(7.0, [[(0.0, 2.0), (DAY, 2.0)]], times, boundaries=boundaries)

    assert result == pytest.approx(expected)


def test_present_value_alone_repeats() -> None:
    """Without a forecast, the present value repeats across the horizon."""
    assert fuse_sensor_payloads(4.0, [], [0.0, HOUR, 2 * HOUR], boundaries=False) == [4.0, 4.0]


@pytest.mark.parametrize(
    ("boundaries", "expected"),
    [
        pytest.param(False, [0.0, 0.0], id="intervals"),
        pytest.param(True, [0.0, 0.0, 0.0], id="boundaries"),
    ],
)
def test_no_data_points_sum_to_zero(*, boundaries: bool, expected: list[float]) -> None:
    """Sources that supplied only forecasts with no points, such as an empty calendar, sum to zero."""
    assert fuse_sensor_payloads(None, [], [0.0, HOUR, 2 * HOUR], boundaries=boundaries) == expected
