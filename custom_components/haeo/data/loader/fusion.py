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

    Fills the horizon by:
    1. Using forecast data directly where available
    2. Cycling through 24-hour blocks when beyond the forecast range
    """

    if not forecast_series:
        return [float(present_value) for _ in range(max(len(horizon_times) - 1, 0))]

    horizon_start = horizon_times[0]
    horizon_end = horizon_times[-1]

    block, cover_seconds = normalize_forecast_cycle(forecast_series, horizon_start)

    # Repeat cover_seconds as needed to cover the horizon
    repeat_count = max(1, int(np.ceil((horizon_end - horizon_start) / cover_seconds)))
    extended_block = [
        (timestamp + i * cover_seconds, value) for i in range(repeat_count) for (timestamp, value) in block
    ]
    block_array = np.array(extended_block, dtype=[("timestamp", np.int64), ("value", np.float64)])

    # Insert the present_value at horizon_start, overwriting any existing value
    insert_idx = np.searchsorted(block_array["timestamp"], horizon_start, side="left")
    block_array = np.insert(block_array, insert_idx, (horizon_start, present_value))

    # Now downsample to the horizon times by summing the values in between using a trapezoidal rule
    # Cumulative integral of the piecewise linear signal
    # This uses trapezoidal integration
    cum = np.concatenate(
        [[0], np.cumsum(np.diff(block_array["timestamp"]) * (block_array["value"][:-1] + block_array["value"][1:]) / 2)]
    )

    # Interpolate cumulative area to new timestamps
    cum_target = np.interp(horizon_times, block_array["timestamp"], cum)

    # Differences to get "average value over intervals"
    v_target = np.diff(cum_target) / np.diff(horizon_times)

    return [float(value) for value in v_target]
