"""Fuse combined forecast data into horizon-aligned values."""

from collections.abc import Sequence

import numpy as np

from custom_components.haeo.data.util.forecast_cycle import normalize_forecast_cycle

from . import ForecastSeries


def fuse_to_horizon(
    present_value: float | None,
    forecast_series: ForecastSeries,
    horizon_times: Sequence[int],
) -> list[float]:
    """Fuse a combined forecast into interval values aligned with the requested horizon.

    Args:
        present_value: Current sensor value (actual current state)
        forecast_series: Time series forecast data
        horizon_times: Boundary timestamps (n_periods+1 values representing interval boundaries)

    Returns:
        n_periods interval values where:
        - Position 0: Present value at horizon_times[0] (actual current state)
        - Position k (k≥1): Interval average over [horizon_times[k] → horizon_times[k+1]]

    The present_value only replaces the first interval and does NOT influence
    subsequent forecast interval calculations. All forecast intervals (position 1+)
    are computed purely from forecast data using trapezoidal integration.

    Fills the horizon by:
    1. Computing forecast interval averages using trapezoidal integration
    2. Cycling through 24-hour blocks when beyond the forecast range
    3. Replacing position 0 with present_value if provided

    """

    if not horizon_times:
        return []

    # Can't make any values if both forecast and present_value are missing
    if not forecast_series and present_value is None:
        msg = "Either forecast_series or present_value must be provided."
        raise ValueError(msg)

    # Just a present value, no forecast
    if not forecast_series and present_value is not None:
        # Return n_periods values (len(horizon_times) - 1), all set to present_value (or 0.0 if None)
        return [present_value] * (len(horizon_times) - 1)

    horizon_start = horizon_times[0]
    # We need to extend beyond the last timestamp to compute the final interval average
    period = horizon_times[1] - horizon_times[0] if len(horizon_times) > 1 else 3600
    horizon_end = horizon_times[-1] + period

    block, cover_seconds = normalize_forecast_cycle(forecast_series, horizon_start)

    # Repeat cover_seconds as needed to cover the entire extended horizon
    # We need at least 2 repetitions to ensure we can interpolate beyond the original forecast
    repeat_count = max(2, int(np.ceil((horizon_end - horizon_start) / cover_seconds)) + 1)
    block = [(timestamp + i * cover_seconds, value) for i in range(repeat_count) for (timestamp, value) in block]
    block_array = np.array(block, dtype=[("timestamp", np.int64), ("value", np.float64)])

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
    # For n+1 boundary timestamps, we need only n intervals
    horizon_indices = np.searchsorted(expanded_block_array["timestamp"], horizon_times)
    cum_target = cum[horizon_indices]

    # Compute interval averages for all intervals
    # np.diff(cum_target) gives us n_periods differences (one per interval between boundaries)
    # np.diff(horizon_times) gives us n_periods time differences
    v_target = np.diff(cum_target) / np.diff(horizon_times)

    # v_target now has len(horizon_times) - 1 values (one per interval)
    # If present_value was provided, replace the first interval with it
    fused = [float(value) for value in v_target]
    fused[0] = present_value if present_value is not None else fused[0]
    return fused
