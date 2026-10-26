"""Utilities for combining sensor payloads into one horizon-aligned series."""

from collections.abc import Mapping, Sequence
import itertools

import numpy as np

from . import ForecastSeries, SensorPayload
from .forecast_fuser import build_extended_block, fuse_to_boundaries, fuse_to_intervals


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
    """End a forecast just before its last timestamp, holding the value it reaches there.

    A forecast that already steps at its last timestamp ends on the point
    before that step.
    """
    *points, (timestamp, value) = series
    before = float(np.nextafter(timestamp, -np.inf))
    if points and points[-1][0] == before:
        return points
    return [*points, (before, value)]


def _windows(forecast_series: Sequence[ForecastSeries]) -> list[tuple[float, float]]:
    """Return the times the forecasts have data as disjoint windows in time order.

    Forecasts whose ranges overlap or meet share one window.
    """
    windows: list[tuple[float, float]] = []
    for start, end in sorted((series[0][0], series[-1][0]) for series in forecast_series):
        if windows and start <= windows[-1][1]:
            windows[-1] = (windows[-1][0], max(windows[-1][1], end))
        else:
            windows.append((start, end))
    return windows


def _merge_forecasts(
    forecast_series: Sequence[ForecastSeries], windows: Sequence[tuple[float, float]]
) -> ForecastSeries:
    """Sum forecasts on one timeline, each counting only within its own range.

    Each forecast steps to zero just outside its range. Where one forecast
    ends at the timestamp a later one starts, the later one alone sets the
    value there: the ending forecast steps down just before it, so the merged
    forecast steps from one to the other. The merged forecast holds points
    only within the windows.
    """
    forecast_series = [
        _end_before(series) if any(other[0][0] == series[-1][0] < other[-1][0] for other in forecast_series) else series
        for series in forecast_series
    ]
    edges = {
        edge
        for series in forecast_series
        for edge in (float(np.nextafter(series[0][0], -np.inf)), float(np.nextafter(series[-1][0], np.inf)))
    }
    all_timestamps = np.array(sorted({timestamp for series in forecast_series for timestamp, _ in series} | edges))
    inside = np.zeros(all_timestamps.size, dtype=bool)
    for start, end in windows:
        inside |= (all_timestamps >= start) & (all_timestamps <= end)
    all_timestamps = all_timestamps[inside]
    total_values = np.zeros(all_timestamps.size, dtype=np.float64)

    for series in forecast_series:
        timestamps = np.array([timestamp for timestamp, _ in series], dtype=np.float64)
        values = np.array([value for _, value in series], dtype=np.float64)
        total_values += np.interp(all_timestamps, timestamps, values, left=0.0, right=0.0)

    return list(zip(all_timestamps.tolist(), total_values.tolist(), strict=True))


def _fill_gaps(merged: ForecastSeries, windows: Sequence[tuple[float, float]]) -> ForecastSeries:
    """Fill the time between windows with the forecast before it repeating by time of day.

    The repeat ends just before the next window starts, so the forecast steps
    from the repeat to the next window's data.
    """
    filled = [point for point in merged if point[0] <= windows[0][1]]
    for (_, gap_start), (gap_end, window_end) in itertools.pairwise(windows):
        block = build_extended_block(filled, filled[0][0], gap_end)
        times, values = block["timestamp"], block["value"]
        in_gap = (times > gap_start) & (times < gap_end)
        repeat = [
            (gap_start, float(np.interp(gap_start, times, values))),
            *zip(times[in_gap].tolist(), values[in_gap].tolist(), strict=True),
            (gap_end, float(np.interp(gap_end, times, values))),
        ]
        filled = [
            *_end_before(filled),
            *_end_before(repeat),
            *(point for point in merged if gap_end <= point[0] <= window_end),
        ]
    return filled


def fuse_sensor_payloads(
    present_value: float | None,
    forecast_series: Sequence[ForecastSeries],
    horizon_times: Sequence[float],
    *,
    boundaries: bool,
) -> list[float]:
    """Fuse sensor payloads to the horizon and sum them.

    All of an input's sensors add up on one timeline, each counting only
    within its own forecast window. Wherever no sensor has data, the combined
    forecast repeats by time of day.

    The present value is the value for now: it replaces the first interval
    (or boundary), and repeats across the horizon when there is no forecast.
    Sources that supplied neither, only forecasts with no points, sum to zero.
    """
    fuse = fuse_to_boundaries if boundaries else fuse_to_intervals
    if not forecast_series:
        if present_value is None:
            return [0.0] * (len(horizon_times) if boundaries else max(len(horizon_times) - 1, 0))
        return fuse(present_value, [], horizon_times)

    windows = _windows(forecast_series)
    return fuse(present_value, _fill_gaps(_merge_forecasts(forecast_series, windows), windows), horizon_times)
