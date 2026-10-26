"""Tests for combining sensor payloads into one horizon-aligned series."""

import numpy as np
import pytest

from custom_components.haeo.core.data.util.forecast_combiner import fuse_sensor_payloads, split_sensor_payloads
from custom_components.haeo.core.data.util.forecast_fuser import fuse_to_intervals

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


# Midnight UTC on 25 October 2025: epoch times, as real forecasts use, keep a step just
# before a timestamp apart from it through the forecast cycle
T0 = 20_386 * DAY


def _flat(start: float, end: float, value: float) -> list[tuple[float, float]]:
    """Return a forecast holding one value from start to end."""
    return [(T0 + start, value), (T0 + end, value)]


def _solar_day(day: int, peak: float) -> list[tuple[float, float]]:
    """Return an hourly solar-like forecast for one whole day, from its midnight to the next."""
    return [(T0 + day * DAY + hour * HOUR, peak * max(0.0, np.sin(np.pi * (hour - 8) / 9))) for hour in range(25)]


def _times(start: float, end: float, step: float) -> list[float]:
    """Return horizon boundaries from start to end."""
    return [T0 + float(time) for time in np.arange(start, end + step / 2, step)]


@pytest.mark.parametrize("end", [18 * HOUR, 23.75 * HOUR, DAY], ids=["18:00", "23:45", "midnight"])
def test_forecast_after_the_horizon_adds_nothing(end: float) -> None:
    """Today's and tomorrow's forecasts on one input give today's alone for a horizon ending today."""
    today = _solar_day(0, 1.0)
    tomorrow = _solar_day(1, 1.5)
    times = _times(0.75 * HOUR, end, 0.25 * HOUR)

    result = fuse_sensor_payloads(None, [today, tomorrow], times, boundaries=False)

    assert result == pytest.approx(fuse_to_intervals(None, today, times))


@pytest.mark.parametrize(
    ("forecast_series", "start", "end", "expected"),
    [
        pytest.param(
            [_flat(0.0, DAY, 1.0), _flat(DAY, 2 * DAY, 3.0)],
            6 * HOUR,
            66 * HOUR,
            [1.0, 2.0, 3.0, 2.0, 1.0],
            id="consecutive_windows_join_then_repeat",
        ),
        pytest.param(
            [_flat(0.0, DAY, 1.0), _flat(0.0, DAY, 2.0)],
            0.0,
            2 * DAY,
            [3.0, 3.0, 3.0, 3.0],
            id="overlapping_windows_add_up",
        ),
        pytest.param(
            [[(T0, 1.0)], [(T0, 2.0)]],
            0.0,
            DAY,
            [3.0, 3.0],
            id="forecasts_at_one_instant_add_up",
        ),
        pytest.param(
            [_flat(0.0, DAY, 1.0), _flat(12 * HOUR, 36 * HOUR, 2.0)],
            0.0,
            36 * HOUR,
            [1.0, 3.0, 2.0],
            id="partial_overlap_adds_in_the_overlap",
        ),
        pytest.param(
            [_flat(0.0, DAY, 1.0), _flat(0.0, 7 * DAY, 10.0)],
            0.0,
            2 * DAY,
            [11.0, 11.0, 10.0, 10.0],
            id="short_window_beside_one_covering_the_horizon_does_not_repeat",
        ),
    ],
)
def test_each_forecast_counts_within_its_own_window(
    forecast_series: list[list[tuple[float, float]]], start: float, end: float, expected: list[float]
) -> None:
    """Forecasts add up on one timeline, each counting only within its own window."""
    result = fuse_sensor_payloads(None, forecast_series, _times(start, end, 12 * HOUR), boundaries=False)

    assert result == pytest.approx(expected)


@pytest.mark.parametrize(
    "later",
    [
        pytest.param([], id="after_a_single_forecast"),
        pytest.param([_flat(2 * DAY, 3 * DAY, 5.0)], id="between_two_windows"),
    ],
)
def test_time_with_no_data_repeats_by_time_of_day(later: list[list[tuple[float, float]]]) -> None:
    """Where no forecast has data, the combined forecast repeats today's profile by time of day."""
    today = _solar_day(0, 1.0)

    result = fuse_sensor_payloads(None, [today, *later], _times(DAY, 2 * DAY, HOUR), boundaries=False)

    assert result == pytest.approx(fuse_to_intervals(None, today, _times(0.0, DAY, HOUR)), abs=1e-6)


def test_forecasts_with_different_coverage_repeat_after_joining() -> None:
    """A shorter forecast joins a longer one and their sum repeats, so the shorter one never fills a whole day."""
    times = [0.0, 12 * HOUR, DAY, DAY + 12 * HOUR, 2 * DAY]
    full_day = [(hour * HOUR, 1.0) for hour in range(24)]
    half_day = [(hour * HOUR, 2.0) for hour in range(13)]

    result = fuse_sensor_payloads(None, [full_day, half_day], times, boundaries=False)

    assert result == pytest.approx([3.0, 1.0, 3.0, 1.0], abs=0.1)


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


# An epoch time, as real forecasts use: the forecast cycle rounds a step just before a small timestamp onto it
SEAM = 1_761_451_200.0


@pytest.mark.parametrize(
    "retailer",
    [
        pytest.param([(SEAM - HOUR, 0.1925), (SEAM, 0.1925)], id="ends_flat"),
        pytest.param(
            [(SEAM - HOUR, 0.1925), (float(np.nextafter(SEAM, -np.inf)), 0.1925), (SEAM, 0.5)], id="ends_in_a_step"
        ),
    ],
)
@pytest.mark.parametrize(
    ("boundaries", "expected"),
    [
        pytest.param(False, [0.1925] * 12 + [0.1979] * 12, id="intervals"),
        pytest.param(True, [0.1925] * 12 + [0.1979] * 13, id="boundaries"),
    ],
)
def test_forecasts_sharing_an_endpoint_step_to_the_later_one(
    retailer: list[tuple[float, float]], *, boundaries: bool, expected: list[float]
) -> None:
    """Where one forecast ends at the timestamp the next starts, the later one alone sets the value there."""
    times = [SEAM - HOUR + step * 300.0 for step in range(25)]
    pre_dispatch = [(SEAM, 0.1979), (SEAM + HOUR, 0.1979)]

    result = fuse_sensor_payloads(None, [retailer, pre_dispatch], times, boundaries=boundaries)

    assert result == pytest.approx(expected)
