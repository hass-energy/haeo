"""Fuse combined forecast data into horizon-aligned values."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from custom_components.haeo.data.util.forecast_cycle import normalize_forecast_cycle

type ForecastSeries = list[tuple[int, float]]


def fuse_to_horizon(
    present_value: float,
    forecast_series: ForecastSeries,
    horizon_times: Sequence[int],
) -> list[float]:
    """Fuse a combined forecast into interval values aligned with the requested horizon.

    Returns n values for n timestamps where:
    - Position 0: Present value at horizon_times[0] (rounded current time)
    - Position k (k≥1): Interval average over [horizon_times[k-1] → horizon_times[k]]

    Fills the horizon by:
    1. Using forecast data directly where available
    2. Cycling through 24-hour blocks when beyond the forecast range
    """

    if not horizon_times:
        return []

    if not forecast_series:
        return [float(present_value) for _ in range(len(horizon_times))]

    horizon_start = horizon_times[0]
    # We need to extend beyond the last timestamp to compute the final interval average
    period = horizon_times[1] - horizon_times[0] if len(horizon_times) > 1 else 3600
    horizon_end = horizon_times[-1] + period

    block, cover_seconds = normalize_forecast_cycle(forecast_series, horizon_start)

    # Insert present_value at horizon_start into the block
    # First, check if there's already a point at horizon_start
    block_list = list(block)
    block_array_temp = np.array(block_list, dtype=[("timestamp", np.int64), ("value", np.float64)])
    idx = np.searchsorted(block_array_temp["timestamp"], horizon_start)

    if idx < len(block_array_temp) and block_array_temp["timestamp"][idx] == horizon_start:
        # Replace existing value
        block_array_temp["value"][idx] = present_value
        block_with_present = block_array_temp.tolist()
    else:
        # Insert new point
        block_with_present = [*block_list[:idx], (horizon_start, present_value), *block_list[idx:]]

    # Repeat cover_seconds as needed to cover the entire extended horizon
    # We need at least 2 repetitions to ensure we can interpolate beyond the original forecast
    repeat_count = max(2, int(np.ceil((horizon_end - horizon_start) / cover_seconds)) + 1)
    extended_block = [
        (timestamp + i * cover_seconds, value) for i in range(repeat_count) for (timestamp, value) in block_with_present
    ]
    block_array = np.array(extended_block, dtype=[("timestamp", np.int64), ("value", np.float64)])

    # Add horizon timestamps to block_array so we can compute exact cumulative values at those points
    # Combine block_array timestamps and horizon_times, removing duplicates
    all_timestamps = np.union1d(block_array["timestamp"], horizon_times)
    all_values = np.interp(all_timestamps, block_array["timestamp"], block_array["value"])

    # Create expanded block array with all timestamps
    expanded_block_array = np.empty(len(all_timestamps), dtype=[("timestamp", np.int64), ("value", np.float64)])
    expanded_block_array["timestamp"] = all_timestamps
    expanded_block_array["value"] = all_values

    # Now compute cumulative integral using trapezoidal rule
    time_diffs = np.diff(expanded_block_array["timestamp"])
    value_averages = (expanded_block_array["value"][:-1] + expanded_block_array["value"][1:]) / 2
    cum = np.concatenate([[0], np.cumsum(time_diffs * value_averages)])

    # Extract cumulative values at horizon timestamps
    horizon_indices = np.searchsorted(expanded_block_array["timestamp"], horizon_times)
    cum_target = cum[horizon_indices]

    # Compute interval averages for positions 1 to n-1
    v_target = np.diff(cum_target) / np.diff(horizon_times)

    # Return n values: present value at position 0, followed by n-1 interval averages
    return [float(present_value)] + [float(value) for value in v_target]
