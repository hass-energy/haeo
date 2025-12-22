"""Loader for building forecasts from sensor historical statistics.

When a sensor doesn't have a forecast attribute, this loader fetches
historical statistics and projects them forward by N days to create a forecast.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.haeo.data.util import ForecastSeries

if TYPE_CHECKING:
    from homeassistant.components.recorder.statistics import StatisticsRow

_LOGGER = logging.getLogger(__name__)

# Default number of days of history to use for forecast
DEFAULT_HISTORY_DAYS = 7

# Maximum cycles to prevent infinite loops in cycle_forecast_to_horizon
_MAX_CYCLES = 100


async def get_statistics_for_sensor(
    hass: HomeAssistant,
    entity_id: str,
    start_time: datetime,
    end_time: datetime,
) -> Sequence[StatisticsRow]:
    """Fetch hourly statistics for a sensor entity.

    Args:
        hass: Home Assistant instance
        entity_id: The sensor entity ID to fetch statistics for
        start_time: Start of the time range
        end_time: End of the time range

    Returns:
        List of statistics rows with 'start' and 'mean' fields.

    Raises:
        ValueError: If the recorder is not available or not set up.

    """
    if "recorder" not in hass.config.components:
        msg = "Recorder component not loaded"
        raise ValueError(msg)

    try:
        from homeassistant.helpers.recorder import DATA_INSTANCE  # noqa: PLC0415

        if DATA_INSTANCE not in hass.data:
            msg = "Recorder not initialized"
            raise ValueError(msg)
    except ImportError:
        msg = "Recorder component not available"
        raise ValueError(msg) from None

    from homeassistant.components.recorder.statistics import statistics_during_period  # noqa: PLC0415

    try:
        statistics: dict[str, list[StatisticsRow]] = await hass.async_add_executor_job(
            lambda: statistics_during_period(
                hass,
                start_time,
                end_time,
                {entity_id},
                "hour",
                None,
                {"mean"},
            )
        )
    except Exception as e:
        msg = f"Failed to fetch statistics: {e}"
        raise ValueError(msg) from e

    return statistics.get(entity_id, [])


def shift_history_to_forecast(
    statistics: Sequence[Any],
    history_days: int,
) -> ForecastSeries:
    """Shift historical statistics forward by N days to create a forecast.

    Takes the raw hourly statistics and shifts each timestamp forward
    by `history_days` to project them into the future.

    Args:
        statistics: List of statistics rows with 'start' and 'mean' fields.
        history_days: Number of days to shift forward.

    Returns:
        ForecastSeries: List of (timestamp, value) tuples for the forecast.

    """
    forecast: ForecastSeries = []
    shift = timedelta(days=history_days)

    for stat in statistics:
        start = stat.get("start")
        mean = stat.get("mean")

        if start is None or mean is None:
            continue

        # Convert start to datetime if needed
        if isinstance(start, datetime):
            dt_start = start
        elif isinstance(start, (int, float)):
            dt_start = datetime.fromtimestamp(start, tz=dt_util.get_default_time_zone())
        else:
            continue

        # Shift forward by N days
        future_time = dt_start + shift
        forecast.append((future_time.timestamp(), float(mean)))

    # Sort by timestamp
    forecast.sort(key=lambda x: x[0])
    return forecast


def cycle_forecast_to_horizon(
    forecast: ForecastSeries,
    history_days: int,
    horizon_end: float,
) -> ForecastSeries:
    """Repeat/cycle forecast series until it covers the full horizon.

    If we have N days of history and the horizon extends beyond that,
    repeat the pattern by shifting forward by N days each cycle.

    Args:
        forecast: Original forecast series (already shifted once)
        history_days: Number of days in one cycle
        horizon_end: Timestamp of the end of the horizon to fill

    Returns:
        Extended ForecastSeries covering the full horizon.

    """
    if not forecast:
        return forecast

    # Get the span of one cycle
    cycle_duration = timedelta(days=history_days).total_seconds()

    # Find when the current forecast ends
    last_timestamp = forecast[-1][0]

    # Keep adding cycles until we cover the horizon
    extended: ForecastSeries = list(forecast)
    cycle_count = 1

    while last_timestamp < horizon_end:
        cycle_shift = cycle_duration * cycle_count
        for original_time, value in forecast:
            new_time = original_time + cycle_shift
            if new_time > horizon_end:
                break
            extended.append((new_time, value))
            last_timestamp = new_time
        cycle_count += 1

        # Safety limit to prevent infinite loops
        if cycle_count > _MAX_CYCLES:
            break

    return extended


class HistoricalForecastLoader:
    """Loader that builds forecasts from sensor historical statistics.

    When a sensor doesn't have a forecast attribute, this loader fetches
    historical data, shifts it forward, and repeats to fill the horizon.
    """

    def __init__(self, history_days: int = DEFAULT_HISTORY_DAYS) -> None:
        """Initialize the loader.

        Args:
            history_days: Number of days of history to fetch and shift forward.

        """
        self._history_days = history_days

    def available(self, *, hass: HomeAssistant, value: Any, **_kwargs: Any) -> bool:
        """Check if we can load data for the given sensor.

        Args:
            hass: Home Assistant instance
            value: Sensor entity ID or list of entity IDs

        Returns:
            True if the recorder component is available and sensors exist.

        """
        if "recorder" not in hass.config.components:
            return False

        entity_ids = self._normalize_entity_ids(value)
        if not entity_ids:
            return False

        return all(hass.states.get(entity_id) is not None for entity_id in entity_ids)

    def _normalize_entity_ids(self, value: Any) -> list[str]:
        """Convert value to a list of entity IDs."""
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple)):
            return [str(v) for v in value if v]
        return []

    async def load(
        self,
        *,
        hass: HomeAssistant,
        value: Any,
        forecast_times: Sequence[float],
        **_kwargs: Any,
    ) -> ForecastSeries:
        """Load historical data and build a forecast by shifting it forward.

        Returns a ForecastSeries that can be passed to fuse_to_horizon.
        The series is cycled/repeated to cover the full forecast horizon.

        Args:
            hass: Home Assistant instance
            value: Sensor entity ID or list of entity IDs
            forecast_times: Timestamps for the forecast horizon

        Returns:
            ForecastSeries (list of (timestamp, value) tuples).

        """
        if not forecast_times:
            return []

        entity_ids = self._normalize_entity_ids(value)
        if not entity_ids:
            msg = "No sensor entity IDs provided"
            raise ValueError(msg)

        # Calculate time range for history - strictly N days back from now
        now = dt_util.now()
        start_time = now - timedelta(days=self._history_days)
        end_time = now

        # Fetch and combine forecast series from all sensors
        combined_forecast: dict[float, float] = {}

        for entity_id in entity_ids:
            try:
                statistics = await get_statistics_for_sensor(hass, entity_id, start_time, end_time)
            except ValueError as e:
                _LOGGER.warning("Failed to get statistics for %s: %s", entity_id, e)
                continue

            if not statistics:
                _LOGGER.debug("No statistics found for %s", entity_id)
                continue

            # Shift history forward to create forecast
            forecast_series = shift_history_to_forecast(statistics, self._history_days)

            # Sum values from multiple sensors at the same timestamp
            for timestamp, value_at_time in forecast_series:
                combined_forecast[timestamp] = combined_forecast.get(timestamp, 0.0) + value_at_time

        if not combined_forecast:
            msg = f"No historical data available for sensors: {entity_ids}"
            raise ValueError(msg)

        # Convert to sorted list of (timestamp, value) tuples
        forecast_series = sorted(combined_forecast.items(), key=lambda x: x[0])

        # Cycle/repeat to fill the full horizon
        horizon_end = forecast_times[-1]
        return cycle_forecast_to_horizon(forecast_series, self._history_days, horizon_end)


# Keep backward compatibility alias
HistoricalLoadLoader = HistoricalForecastLoader
