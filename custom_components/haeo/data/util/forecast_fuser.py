"""Fuse combined forecast data into horizon-aligned values."""

from collections.abc import Sequence
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.data.util.forecast_cycle import normalize_forecast_cycle

from . import ForecastSeries

# Need at least 2 boundaries (start and end) to define one interval
MIN_BOUNDARIES = 2

# Interpolation modes for time series data
type InterpolationMode = Literal["linear", "step"]


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


def _step_interp(
    query_times: Sequence[float],
    timestamps: NDArray[np.floating[Any]],
    values: NDArray[np.floating[Any]],
) -> NDArray[np.floating[Any]]:
    """Step interpolation (zero-order hold): return the value at or before each query time.

    For each query time, returns the value from the most recent timestamp that is
    less than or equal to the query time. If query time is before all timestamps,
    returns the first value.

    Args:
        query_times: Times at which to look up values
        timestamps: Sorted array of forecast timestamps
        values: Array of values corresponding to timestamps

    Returns:
        Array of values at each query time using step interpolation

    """
    # searchsorted with side='right' gives index where query_time would be inserted
    # to maintain sorted order. Subtracting 1 gives the index of the largest
    # timestamp <= query_time (or -1 if query_time < all timestamps).
    indices = np.searchsorted(timestamps, query_times, side="right") - 1
    # Clamp to valid range [0, len-1] for edge cases
    indices = np.clip(indices, 0, len(values) - 1)
    return values[indices]


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
    interpolation: InterpolationMode = "linear",
) -> list[float]:
    """Fuse a combined forecast into interval averages aligned with the horizon.

    Args:
        present_value: Current sensor value (actual current state)
        forecast_series: Time series forecast data
        horizon_times: Boundary timestamps (n+1 values defining n intervals)
        interpolation: How to interpolate between forecast points:
            - "linear": Values change linearly between points (power, efficiency)
            - "step": Values hold until the next point (prices)

    Returns:
        n interval values where:
        - Position 0: Present value (actual current state) if provided, else computed from forecast
        - Position k (k≥1): Computed value over interval [horizon_times[k], horizon_times[k+1]]

    For linear interpolation, trapezoidal integration computes accurate interval averages.
    For step interpolation, the weighted average of step segments is computed.

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

    if interpolation == "step":
        result = _fuse_step_intervals(block_array, horizon_times, n_intervals)
    else:
        result = _fuse_linear_intervals(block_array, horizon_times, n_intervals)

    # Replace first interval with present_value if provided
    if present_value is not None:
        result[0] = present_value

    return result


def _fuse_linear_intervals(
    block_array: NDArray[Any],
    horizon_times: Sequence[float],
    n_intervals: int,
) -> list[float]:
    """Compute interval values using linear interpolation and trapezoidal integration."""
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

    return result


def _fuse_step_intervals(
    block_array: NDArray[Any],
    horizon_times: Sequence[float],
    n_intervals: int,
) -> list[float]:
    """Compute interval values using step interpolation (weighted average of step segments)."""
    result: list[float] = []
    timestamps = block_array["timestamp"]
    values = block_array["value"]

    for i in range(n_intervals):
        interval_start = horizon_times[i]
        interval_end = horizon_times[i + 1]
        interval_duration = interval_end - interval_start

        # Get block points within or at the start of this interval
        # Include points at interval_start, exclude points at interval_end
        mask = (timestamps >= interval_start) & (timestamps < interval_end)
        interval_points_mask = mask

        if not np.any(interval_points_mask):
            # No forecast points in this interval - use step value from before
            step_value = _step_interp([interval_start], timestamps, values)[0]
            result.append(float(step_value))
        else:
            # Compute weighted average of step segments
            # Each segment runs from one timestamp to the next (or interval end)
            interval_timestamps = timestamps[interval_points_mask]
            interval_values = values[interval_points_mask]

            # Add the value that applies at interval_start if it's before first point
            if interval_timestamps[0] > interval_start:
                start_value = _step_interp([interval_start], timestamps, values)[0]
                interval_timestamps = np.concatenate([[interval_start], interval_timestamps])
                interval_values = np.concatenate([[start_value], interval_values])

            # Compute segment durations and weighted sum
            # Each value applies from its timestamp until the next timestamp (or interval_end)
            segment_ends = np.concatenate([interval_timestamps[1:], [interval_end]])
            segment_durations = segment_ends - interval_timestamps
            weighted_sum = np.sum(interval_values * segment_durations)
            result.append(float(weighted_sum / interval_duration))

    return result
