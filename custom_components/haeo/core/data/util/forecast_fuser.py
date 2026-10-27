"""Fuse combined forecast data into horizon-aligned values."""

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.data.util.forecast_cycle import normalize_forecast_cycle

from . import ForecastSeries

# Need at least 2 boundaries (start and end) to define one interval
MIN_BOUNDARIES = 2


def build_extended_block(
    forecast_series: ForecastSeries,
    horizon_start: float,
    horizon_end: float,
) -> NDArray[np.void]:
    """Build extended forecast block covering the horizon with cycling.

    Args:
        forecast_series: Time series forecast data (must not be empty)
        horizon_start: Start of the horizon
        horizon_end: End of the horizon

    Returns:
        Structured numpy array with 'timestamp' and 'value' fields

    """
    block, cover_seconds = normalize_forecast_cycle(forecast_series, horizon_start)

    # Repeat block as needed to cover the entire horizon, starting one cycle early
    # to provide interpolation context before horizon_start
    repeat_count = max(2, int(np.ceil((horizon_end - horizon_start) / cover_seconds)) + 1)
    block_array = np.array(block, dtype=[("timestamp", np.float64), ("value", np.float64)])
    extended = np.tile(block_array, repeat_count + 1)
    extended["timestamp"] += np.repeat(np.arange(-1, repeat_count) * cover_seconds, len(block_array))
    return extended


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

    block_array = build_extended_block(forecast_series, horizon_times[0], horizon_times[-1])

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

    block_array = build_extended_block(forecast_series, horizon_times[0], horizon_times[-1])
    block_times = block_array["timestamp"]
    block_values = block_array["value"]
    boundaries = np.asarray(horizon_times, dtype=np.float64)

    # Integrate the piecewise linear forecast through each interval's internal block
    # points and its boundaries. A block point exactly on a boundary is replaced by
    # the interpolated boundary value, as the block may hold a step there.
    internal = ~np.isin(block_times, boundaries)
    times = np.concatenate([block_times[internal], boundaries])
    values = np.concatenate([block_values[internal], np.interp(boundaries, block_times, block_values)])
    order = np.argsort(times, kind="stable")
    times = times[order]
    values = values[order]
    segment_areas = np.diff(times) * (values[:-1] + values[1:]) / 2

    # Sum the segments lying between consecutive boundaries, then average over each interval
    boundary_positions = np.flatnonzero(order >= np.count_nonzero(internal))
    areas = np.add.reduceat(segment_areas[: boundary_positions[-1]], boundary_positions[:-1])
    result: list[float] = (areas / np.diff(boundaries)).tolist()

    # Replace first interval with present_value if provided
    if present_value is not None:
        result[0] = present_value

    return result
