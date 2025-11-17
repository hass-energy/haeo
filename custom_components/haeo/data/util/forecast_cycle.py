"""Forecast cycle utilities."""

from typing import Final

import numpy as np

from . import ForecastSeries

_SECONDS_PER_DAY: Final = 24 * 60 * 60


def normalize_forecast_cycle(forecast_series: ForecastSeries, current_time: int) -> tuple[ForecastSeries, int]:
    """Return a 24-hour aligned forecast block starting at ``current_time``."""

    # First take the forecast and repeat it as needed to make it a multiple of 24 hours long
    forecast = np.array(forecast_series, dtype=[("timestamp", np.int64), ("value", np.float64)])
    cover_days = max(1, np.ceil((forecast[-1]["timestamp"] - forecast[0]["timestamp"]) / _SECONDS_PER_DAY))
    cover_seconds = cover_days * _SECONDS_PER_DAY
    end_time = forecast[-1]["timestamp"]
    start_time = forecast[0]["timestamp"]

    forecast_remainder = (end_time - start_time) % _SECONDS_PER_DAY
    forecast_required = _SECONDS_PER_DAY - forecast_remainder

    # This is the time that is earliest in the forecast at the same time of day as the end time
    extra_start = start_time + forecast_remainder
    extra_end = extra_start + forecast_required
    extra_start_idx = np.searchsorted(forecast["timestamp"], extra_start, side="right")
    extra_end_idx = np.searchsorted(forecast["timestamp"], extra_end, side="left")

    # Wrap the extra part to the end to fill out the day
    delta_t = end_time - extra_start
    periodic_forecast = np.concatenate([forecast, forecast[extra_start_idx:extra_end_idx]])
    periodic_forecast["timestamp"][len(forecast) :] += delta_t

    # Now shift the entire forecast so that it starts from current_time and wraps around every cover_seconds
    start_offset = cover_seconds + (cover_seconds - (current_time % cover_seconds))
    forecast_times = np.mod(periodic_forecast["timestamp"] + start_offset, cover_seconds) + current_time
    forecast_idx = np.argsort(forecast_times)

    output_forecast = np.empty_like(periodic_forecast)
    output_forecast["timestamp"] = forecast_times[forecast_idx]
    output_forecast["value"] = periodic_forecast["value"][forecast_idx]

    return output_forecast.tolist(), cover_seconds
