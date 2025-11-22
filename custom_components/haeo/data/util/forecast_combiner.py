"""Utilities for combining forecast payloads."""

from collections.abc import Mapping

import numpy as np

from . import ForecastSeries, SensorPayload


def combine_sensor_payloads(payloads: Mapping[str, SensorPayload]) -> tuple[float | None, ForecastSeries]:
    """Sum present values and merge forecast series on shared timestamps."""

    present_value: float | None = None
    forecast_series: list[ForecastSeries] = []

    for payload in payloads.values():
        if isinstance(payload, float):
            if present_value is None:
                present_value = 0.0
            present_value += payload
        elif isinstance(payload, list):
            forecast_series.append(payload)

    if not forecast_series:
        return (present_value, [])

    unique_timestamps = sorted({timestamp for series in forecast_series for timestamp, _ in series})
    all_timestamps = np.array(unique_timestamps, dtype=np.int64)
    total_values = np.zeros(all_timestamps.size, dtype=np.float64)

    for series in forecast_series:
        timestamps = np.array([timestamp for timestamp, _ in series], dtype=np.int64)
        values = np.array([value for _, value in series], dtype=np.float64)
        interpolated = np.interp(all_timestamps, timestamps, values, left=0.0, right=0.0)
        total_values += interpolated

    combined_forecast = [
        (int(timestamp), float(value))
        for timestamp, value in zip(all_timestamps.tolist(), total_values.tolist(), strict=False)
    ]

    return (present_value, combined_forecast)
