"""Utilities for combining sensor payloads into one horizon-aligned series."""

from collections.abc import Mapping, Sequence

import numpy as np

from . import ForecastSeries, SensorPayload
from .forecast_fuser import fuse_to_boundaries, fuse_to_intervals


def split_sensor_payloads(payloads: Mapping[str, SensorPayload]) -> tuple[float | None, list[ForecastSeries]]:
    """Return the summed present values, or None when there are none, and each forecast series.

    A forecast with no points, such as a calendar without events, adds nothing.
    """
    present_value: float | None = None
    forecast_series: list[ForecastSeries] = []

    for payload in payloads.values():
        if isinstance(payload, float):
            present_value = payload if present_value is None else present_value + payload
        elif isinstance(payload, list) and payload:
            forecast_series.append(payload)

    return present_value, forecast_series


def _end_before(series: ForecastSeries) -> ForecastSeries:
    """Move a forecast's last point just before its timestamp, keeping its value."""
    *points, (timestamp, value) = series
    return [*points, (float(np.nextafter(timestamp, -np.inf)), value)]


def _merge_forecasts(forecast_series: Sequence[ForecastSeries]) -> ForecastSeries:
    """Sum forecasts on the union of their timestamps, each zero outside its own range.

    Where one forecast ends at the timestamp another starts, the later one
    alone sets the value there: the ending forecast steps down just before
    it, so the merged forecast steps from one to the other.
    """
    forecast_series = [
        _end_before(series)
        if any(other is not series and other[0][0] == series[-1][0] for other in forecast_series)
        else series
        for series in forecast_series
    ]
    unique_timestamps = sorted({timestamp for series in forecast_series for timestamp, _ in series})
    all_timestamps = np.array(unique_timestamps, dtype=np.float64)
    total_values = np.zeros(all_timestamps.size, dtype=np.float64)

    for series in forecast_series:
        timestamps = np.array([timestamp for timestamp, _ in series], dtype=np.float64)
        values = np.array([value for _, value in series], dtype=np.float64)
        total_values += np.interp(all_timestamps, timestamps, values, left=0.0, right=0.0)

    return list(zip(all_timestamps.tolist(), total_values.tolist(), strict=True))


def _covers(series: ForecastSeries, horizon_times: Sequence[float]) -> bool:
    """Return True when a forecast spans the whole horizon, so it never repeats."""
    return series[0][0] <= horizon_times[0] and series[-1][0] >= horizon_times[-1]


def fuse_sensor_payloads(
    present_value: float | None,
    forecast_series: Sequence[ForecastSeries],
    horizon_times: Sequence[float],
    *,
    boundaries: bool,
) -> list[float]:
    """Fuse sensor payloads to the horizon and sum them.

    Forecasts that only cover part of the horizon merge first, each zero
    outside its own range, so forecasts for consecutive windows (today and
    tomorrow) join into one, which then repeats to fill the horizon. A
    forecast covering the whole horizon fuses on its own and adds to the
    result, so it never stops the partial forecasts from repeating.

    The present value is the value for now: it replaces the first interval
    (or boundary), and repeats across the horizon when there is no forecast.
    Sources that supplied neither, only forecasts with no points, sum to zero.
    """
    fuse = fuse_to_boundaries if boundaries else fuse_to_intervals
    if not forecast_series:
        if present_value is None:
            return [0.0] * (len(horizon_times) if boundaries else max(len(horizon_times) - 1, 0))
        return fuse(present_value, [], horizon_times)

    covering = [series for series in forecast_series if _covers(series, horizon_times)]
    partial = [series for series in forecast_series if not _covers(series, horizon_times)]
    fused = [fuse(None, series, horizon_times) for series in covering]
    if partial:
        fused.append(fuse(None, _merge_forecasts(partial), horizon_times))

    result: list[float] = np.sum(fused, axis=0).tolist()
    if present_value is not None and result:
        result[0] = present_value
    return result
