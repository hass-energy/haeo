"""Utilities for combining sensor payloads into one horizon-aligned series."""

from collections.abc import Mapping, Sequence

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


def _group(forecast_series: Sequence[ForecastSeries]) -> list[list[ForecastSeries]]:
    """Group forecasts that follow on from each other without overlapping.

    Forecasts are taken in order of their start, then their end, then input
    order, and each joins the first group it follows on from: it starts at or
    after the group's end and ends after it. Otherwise it starts a new group.
    """
    groups: list[list[ForecastSeries]] = []
    for series in sorted(forecast_series, key=lambda series: (series[0][0], series[-1][0])):
        group = next(
            (group for group in groups if group[-1][-1][0] <= series[0][0] and group[-1][-1][0] < series[-1][0]),
            None,
        )
        if group is None:
            groups.append([series])
        else:
            group.append(series)
    return groups


def _repeat(forecast: ForecastSeries, start: float, end: float) -> ForecastSeries:
    """Return a forecast repeating by time of day from start to end."""
    block = build_extended_block(forecast, forecast[0][0], end)
    times, values = block["timestamp"], block["value"]
    inside = (times > start) & (times < end)
    return [
        (start, float(np.interp(start, times, values))),
        *zip(times[inside].tolist(), values[inside].tolist(), strict=True),
        (end, float(np.interp(end, times, values))),
    ]


def _join(group: Sequence[ForecastSeries]) -> ForecastSeries:
    """Join forecasts that follow on from each other into one.

    Where one forecast ends at the timestamp the next starts, the later one
    alone sets the value there: the ending forecast steps down just before
    it, so the joined forecast steps from one to the other. A gap between
    two forecasts fills with the forecast before it repeating by time of day,
    which steps to the next forecast where it starts.
    """
    joined = group[0]
    for series in group[1:]:
        gap_start, gap_end = joined[-1][0], series[0][0]
        if gap_start < gap_end:
            joined = [*_end_before(joined), *_repeat(joined, gap_start, gap_end)]
        joined = [*_end_before(joined), *series]
    return joined


def fuse_sensor_payloads(
    present_value: float | None,
    forecast_series: Sequence[ForecastSeries],
    horizon_times: Sequence[float],
    *,
    boundaries: bool,
) -> list[float]:
    """Fuse sensor payloads to the horizon and sum them.

    Sensors whose forecasts follow on from each other without overlapping
    join into one. Each sensor, or joined group, then repeats by time of day
    past its own forecast, and they all add up.

    The present value is the value for now: it replaces the first interval
    (or boundary), and repeats across the horizon when there is no forecast.
    Sources that supplied neither, only forecasts with no points, sum to zero.
    """
    fuse = fuse_to_boundaries if boundaries else fuse_to_intervals
    if not forecast_series:
        if present_value is None:
            return [0.0] * (len(horizon_times) if boundaries else max(len(horizon_times) - 1, 0))
        return fuse(present_value, [], horizon_times)

    fused = [fuse(None, _join(group), horizon_times) for group in _group(forecast_series)]
    result: list[float] = np.sum(fused, axis=0).tolist()
    if present_value is not None and result:
        result[0] = present_value
    return result
