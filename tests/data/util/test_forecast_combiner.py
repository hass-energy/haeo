"""Tests for forecast payload combination utilities."""

from __future__ import annotations

import pytest

from custom_components.haeo.data.util.forecast_combiner import combine_sensor_payloads

type Payloads = dict[str, float | list[tuple[int, float]]]


def test_combine_sensor_payloads_interpolates_and_sums() -> None:
    """Combine sensor payloads interpolates each forecast and sums at unique timestamps."""

    payloads: Payloads = {
        "sensor.a": [(0, 1.0), (3600, 2.0)],
        "sensor.b": [(0, 0.5), (7200, 4.0)],
    }

    present_value, forecast_series = combine_sensor_payloads(payloads)

    assert present_value == 0.0
    assert len(forecast_series) == 3

    timestamp, value = forecast_series[0]
    assert timestamp == 0
    assert value == pytest.approx(1.5)

    timestamp, value = forecast_series[1]
    assert timestamp == 3600
    assert value == pytest.approx(4.25)

    timestamp, value = forecast_series[2]
    assert timestamp == 7200
    assert value == pytest.approx(4.0)


def test_combine_sensor_payloads_handles_non_overlapping_ranges() -> None:
    """Combine sensor payloads correctly handles forecasts with no overlap."""

    payloads: Payloads = {
        "sensor.a": [(0, 10.0), (1000, 20.0)],
        "sensor.b": [(2000, 5.0), (3000, 15.0)],
    }

    present_value, forecast_series = combine_sensor_payloads(payloads)

    assert present_value == 0.0
    assert len(forecast_series) == 4
    timestamps = [ts for ts, _ in forecast_series]
    assert timestamps == [0, 1000, 2000, 3000]

    timestamp, value = forecast_series[0]
    assert timestamp == 0
    assert value == pytest.approx(10.0)

    timestamp, value = forecast_series[1]
    assert timestamp == 1000
    assert value == pytest.approx(20.0)

    timestamp, value = forecast_series[2]
    assert timestamp == 2000
    assert value == pytest.approx(5.0)

    timestamp, value = forecast_series[3]
    assert timestamp == 3000
    assert value == pytest.approx(15.0)


def test_combine_sensor_payloads_handles_single_sensor() -> None:
    """Combine sensor payloads works with a single sensor."""

    payloads: Payloads = {
        "sensor.a": [(0, 1.0), (3600, 2.0), (7200, 3.0)],
    }

    present_value, forecast_series = combine_sensor_payloads(payloads)

    assert present_value == 0.0
    assert len(forecast_series) == 3
    assert forecast_series == [(0, 1.0), (3600, 2.0), (7200, 3.0)]


def test_combine_sensor_payloads_interpolates_at_intermediate_points() -> None:
    """Combine sensor payloads correctly interpolates between points."""

    payloads: Payloads = {
        "sensor.a": [(0, 0.0), (2000, 10.0)],
        "sensor.b": [(1000, 5.0)],
    }

    present_value, forecast_series = combine_sensor_payloads(payloads)

    assert present_value == 0.0
    assert len(forecast_series) == 3
    timestamps = [ts for ts, _ in forecast_series]
    assert timestamps == [0, 1000, 2000]

    timestamp, value = forecast_series[0]
    assert timestamp == 0
    assert value == pytest.approx(0.0)

    timestamp, value = forecast_series[1]
    assert timestamp == 1000
    assert value == pytest.approx(10.0)

    timestamp, value = forecast_series[2]
    assert timestamp == 2000
    assert value == pytest.approx(10.0)


def test_combine_sensor_payloads_separates_floats_and_forecasts() -> None:
    """Combine sensor payloads correctly separates simple floats from forecast series."""

    payloads: Payloads = {
        "sensor.live": 100.0,
        "sensor.live2": 50.0,
        "sensor.forecast": [(0, 10.0), (3600, 20.0)],
    }

    present_value, forecast_series = combine_sensor_payloads(payloads)

    assert present_value == pytest.approx(150.0)
    assert len(forecast_series) == 2
    assert forecast_series == [(0, 10.0), (3600, 20.0)]
