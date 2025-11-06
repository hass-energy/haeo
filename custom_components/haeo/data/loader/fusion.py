"""Combine and fuse sensor payloads into merged time series."""

from collections.abc import Mapping, Sequence

import numpy as np

type ForecastSeries = list[tuple[int, float]]
type SensorPayload = float | ForecastSeries

_SECONDS_PER_DAY = 24 * 60 * 60


def combine_sensor_payloads(payloads: Mapping[str, SensorPayload]) -> tuple[float, ForecastSeries]:
    """Combine sensor payloads by separating present values and forecast series.

    Simple float values are summed as present values.
    Forecast series are interpolated and summed at all unique timestamps.

    Returns:
        Tuple of (present_value, forecast_series) where present_value is the sum of
        all simple values and forecast_series contains the combined forecast data.

    """
    present_value = 0.0
    forecast_series: list[ForecastSeries] = []

    for payload in payloads.values():
        if isinstance(payload, float):
            present_value += payload
        elif isinstance(payload, list):
            forecast_series.append(payload)

    if not forecast_series:
        return (present_value, [])

    all_timestamps = np.array(sorted({ts for series in forecast_series for ts, _ in series}), dtype=np.int64)

    total_values = np.zeros(all_timestamps.size, dtype=np.float64)
    for series in forecast_series:
        timestamps = np.array([ts for ts, _ in series], dtype=np.int64)
        values = np.array([val for _, val in series], dtype=np.float64)

        interpolated = np.interp(all_timestamps, timestamps, values, left=0.0, right=0.0)
        total_values += interpolated

    return (present_value, list(zip(all_timestamps.tolist(), total_values.tolist(), strict=True)))


def fuse_to_horizon(
    present_value: float,
    forecast_series: ForecastSeries,
    horizon_times: Sequence[int],
    *,
    current_time: int | None = None,
) -> list[float]:
    """Fuse combined sensor data into a horizon-aligned time series.

    Combines present values with forecast data, filters old data,
    and resamples to the horizon with daily repetition for coverage gaps.
    """
    forecast = forecast_series

    if current_time is not None:
        forecast = [(ts, val) for ts, val in forecast if ts >= current_time]

    if present_value and forecast:
        forecast = [(current_time or horizon_times[0], present_value), *forecast]
    elif present_value:
        return [present_value] * len(horizon_times)
    elif not forecast:
        return [0.0] * len(horizon_times)

    timestamps = np.array([ts for ts, _ in forecast], dtype=np.int64)
    values = np.array([val for _, val in forecast], dtype=np.float64)

    if timestamps.size == 1:
        return [float(values[0])] * len(horizon_times)

    min_ts, max_ts = int(timestamps[0]), int(timestamps[-1])
    coverage = max_ts - min_ts
    cycle_seconds = (coverage // _SECONDS_PER_DAY) * _SECONDS_PER_DAY if coverage >= _SECONDS_PER_DAY else coverage

    result: list[float] = []
    for target_ts in horizon_times:
        sample_ts = int(target_ts)
        if sample_ts > max_ts and cycle_seconds > 0:
            sample_ts = min_ts + (sample_ts - min_ts) % cycle_seconds
        sample_ts = max(min_ts, min(sample_ts, max_ts))

        result.append(float(np.interp(sample_ts, timestamps, values)))

    return result
