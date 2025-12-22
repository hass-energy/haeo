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

# Minimum number of forecast times needed to produce output
_MIN_FORECAST_TIMES = 2


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


class HistoricalForecastLoader:
    """Loader that builds forecasts from sensor historical statistics.

    When a sensor doesn't have a forecast attribute, this loader fetches
    historical data and shifts it forward by N days to create a forecast.
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
    ) -> list[float]:
        """Load historical data and build a forecast by shifting it forward.

        Args:
            hass: Home Assistant instance
            value: Sensor entity ID or list of entity IDs
            forecast_times: Timestamps for the forecast horizon

        Returns:
            List of power values aligned to forecast_times.

        """
        if not forecast_times:
            return []

        entity_ids = self._normalize_entity_ids(value)
        if not entity_ids:
            msg = "No sensor entity IDs provided"
            raise ValueError(msg)

        # Calculate time range for history
        now = dt_util.now()
        start_time = now - timedelta(days=self._history_days)
        start_time = start_time.replace(minute=0, second=0, microsecond=0)
        end_time = now.replace(minute=0, second=0, microsecond=0)

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

        # Interpolate to align with forecast_times
        return self._interpolate_to_times(forecast_series, forecast_times)

    def _interpolate_to_times(
        self,
        forecast_series: list[tuple[float, float]],
        forecast_times: Sequence[float],
    ) -> list[float]:
        """Interpolate forecast series to match the requested forecast times.

        Args:
            forecast_series: Sorted list of (timestamp, value) tuples
            forecast_times: Target timestamps to interpolate to

        Returns:
            List of values for each interval (len = len(forecast_times) - 1)

        """
        if len(forecast_times) < _MIN_FORECAST_TIMES:
            return []

        result: list[float] = []

        # For each interval, find the corresponding value from forecast series
        for i in range(len(forecast_times) - 1):
            interval_start = forecast_times[i]

            # Find the closest forecast value at or before this time
            value = self._find_value_at_time(forecast_series, interval_start)
            result.append(value)

        return result

    def _find_value_at_time(
        self,
        forecast_series: list[tuple[float, float]],
        target_time: float,
    ) -> float:
        """Find the forecast value for a given time.

        Uses the most recent value at or before the target time.

        Args:
            forecast_series: Sorted list of (timestamp, value) tuples
            target_time: The timestamp to find the value for

        Returns:
            The value at the target time, or 0.0 if no data available.

        """
        if not forecast_series:
            return 0.0

        # Find the last value at or before target_time
        last_value = 0.0
        for timestamp, value in forecast_series:
            if timestamp > target_time:
                break
            last_value = value

        return last_value


# Keep backward compatibility alias
HistoricalLoadLoader = HistoricalForecastLoader
