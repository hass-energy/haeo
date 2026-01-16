"""Fuse combined forecast data into horizon-aligned values."""

from collections.abc import Sequence
from typing import Any

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.data.util.forecast_cycle import normalize_forecast_cycle

from . import ForecastSeries

# Need at least 2 boundaries (start and end) to define one interval
MIN_BOUNDARIES = 2


def _build_extended_block(
    forecast_series: ForecastSeries,
    horizon_start: float,
    horizon_end: float,
) -> NDArray[Any]:
    """Build extended forecast block covering the horizon with cycling.

    Args:
        forecast_series: Time series forecast data (must not be empty)
        horizon_start: Start of the horizon
        horizon_end: End of the horizon

    Returns:
        Structured numpy array with 'timestamp' and 'value' fields

    """
    block, cover_seconds = normalize_forecast_cycle(forecast_series, horizon_start)

    # Repeat block as needed to cover the entire horizon
    repeat_count = max(2, int(np.ceil((horizon_end - horizon_start) / cover_seconds)) + 1)
    extended = [(timestamp + i * cover_seconds, value) for i in range(repeat_count) for (timestamp, value) in block]
    return np.array(extended, dtype=[("timestamp", np.float64), ("value", np.float64)])


def fuse_to_boundaries(
    present_value: float | None,
    forecast_series: ForecastSeries,
    horizon_times: Sequence[float],
) -> list[float]:
    """Fuse a combined forecast into point-in-time values at each horizon boundary.

    Args:
        present_value: Current sensor value (actual current state)
        forecast_series: Time series forecast data
        horizon_times: Boundary timestamps (n+1 values defining n intervals)

    Returns:
        n+1 point-in-time values where:
        - Position 0: Present value at horizon_times[0] (actual current state if provided)
        - Position k (k≥1): Interpolated value at horizon_times[k]

    """
    if not horizon_times:
        return []

    # Can't make any values if both forecast and present_value are missing
    if not forecast_series and present_value is None:
        msg = "Either forecast_series or present_value must be provided."
        raise ValueError(msg)

    # Just a present value, no forecast - return it for all boundaries
    if not forecast_series and present_value is not None:
        return [present_value] * len(horizon_times)

    block_array = _build_extended_block(forecast_series, horizon_times[0], horizon_times[-1])

    # Interpolate at boundary times
    values = np.interp(horizon_times, block_array["timestamp"], block_array["value"])

    # Replace position 0 with present_value if provided
    result = [float(v) for v in values]
    if present_value is not None:
        result[0] = present_value
    return result


def fuse_to_intervals(
    present_value: float | None,
    forecast_series: ForecastSeries,
    horizon_times: Sequence[float],
) -> list[float]:
    """Fuse a combined forecast into interval averages aligned with the horizon.

    Args:
        present_value: Current sensor value (actual current state)
        forecast_series: Time series forecast data
        horizon_times: Boundary timestamps (n+1 values defining n intervals)

    Returns:
        n interval values where:
        - Position 0: Present value (actual current state) if provided, else trapezoidal average
        - Position k (k≥1): Trapezoidal average over interval [horizon_times[k], horizon_times[k+1]]

    Trapezoidal integration accounts for internal forecast points within each interval,
    not just the endpoint values.

    Present value extends to all intervals ending at or before the first forecast point
    that is strictly after horizon_start. This ensures the current value is used until
    actual future forecast data is available.

    """
    if not horizon_times or len(horizon_times) < MIN_BOUNDARIES:
        return []

    n_intervals = len(horizon_times) - 1

    # No forecast: broadcast present value to all intervals
    if not forecast_series:
        if present_value is None:
            msg = "Either forecast_series or present_value must be provided."
            raise ValueError(msg)
        return [present_value] * n_intervals

    horizon_start = horizon_times[0]
    horizon_end = horizon_times[-1]

    block_array = _build_extended_block(forecast_series, horizon_start, horizon_end)

    # Find the first forecast point strictly after horizon_start.
    # Present value extends to all intervals ending at or before this point,
    # since we don't have actual forecast data until then.
    first_future_forecast = None
    if present_value is not None:
        for timestamp, _value in forecast_series:
            if timestamp > horizon_start:
                first_future_forecast = timestamp
                break

    # Trapezoidal integration over each interval
    result: list[float] = []
    for i in range(n_intervals):
        interval_start = horizon_times[i]
        interval_end = horizon_times[i + 1]
        interval_duration = interval_end - interval_start

        # Get block points strictly within this interval (excluding boundaries)
        mask = (block_array["timestamp"] > interval_start) & (block_array["timestamp"] < interval_end)
        interval_points = block_array[mask]

        # Build integration series: start boundary + internal points + end boundary
        start_value = np.interp(interval_start, block_array["timestamp"], block_array["value"])
        end_value = np.interp(interval_end, block_array["timestamp"], block_array["value"])
        times = np.concatenate([[interval_start], interval_points["timestamp"], [interval_end]])
        values = np.concatenate([[start_value], interval_points["value"], [end_value]])

        # Trapezoidal integration: area under curve divided by duration
        area = np.trapezoid(values, times)
        result.append(float(area / interval_duration))

    # Apply present_value to intervals until we have actual forecast data.
    # Extend to all intervals ending at or before the first future forecast point.
    # Round to nearest second to handle nextafter timestamps and fractional horizon times.
    if present_value is not None:
        result[0] = present_value
        if first_future_forecast is not None:
            first_future_rounded = round(first_future_forecast)
            for i in range(1, n_intervals):
                interval_end = horizon_times[i + 1]
                if round(interval_end) <= first_future_rounded:
                    result[i] = present_value
                else:
                    break

    return result
