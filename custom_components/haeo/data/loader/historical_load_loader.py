"""Loader for building forecasts from sensor historical statistics.

When a sensor doesn't have a forecast attribute, this loader fetches
historical statistics and builds a forecast based on the pattern
from the past N days.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, tzinfo
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
    # Check if recorder is available
    if "recorder" not in hass.config.components:
        msg = "Recorder component not loaded"
        raise ValueError(msg)

    # Check if recorder instance is set up
    try:
        from homeassistant.helpers.recorder import DATA_INSTANCE  # noqa: PLC0415

        if DATA_INSTANCE not in hass.data:
            msg = "Recorder not initialized"
            raise ValueError(msg)
    except ImportError:
        msg = "Recorder component not available"
        raise ValueError(msg) from None

    # Import here to avoid circular imports and allow mocking
    from homeassistant.components.recorder.statistics import (  # noqa: PLC0415
        statistics_during_period,
    )

    # Fetch statistics - runs in executor since it's blocking
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


def build_hourly_pattern(
    statistics: Sequence[Any],
    timezone: tzinfo | None = None,
) -> dict[int, float]:
    """Build a 24-hour pattern from historical statistics.

    Groups data by hour-of-day (0-23) and averages across all days.

    Args:
        statistics: List of statistics rows with 'start' and 'mean' fields.
        timezone: Timezone to use for hour-of-day calculation.

    Returns:
        Dictionary mapping hour-of-day (0-23) to average value.

    """
    tz = timezone or dt_util.get_default_time_zone()

    # Group values by hour-of-day and accumulate for averaging
    hour_values: dict[int, list[float]] = {h: [] for h in range(24)}

    for stat in statistics:
        start = stat.get("start")
        mean = stat.get("mean")

        if start is None or mean is None:
            continue

        # Convert to datetime in the target timezone
        if isinstance(start, datetime):
            # Convert to target timezone if timezone-aware
            if start.tzinfo is not None:
                dt_local = start.astimezone(tz)
            else:
                dt_local = start.replace(tzinfo=tz)
            hour_of_day = dt_local.hour
        elif isinstance(start, (int, float)):
            dt_local = datetime.fromtimestamp(start, tz=tz)
            hour_of_day = dt_local.hour
        else:
            continue

        hour_values[hour_of_day].append(float(mean))

    # Calculate average for each hour-of-day
    hourly_pattern: dict[int, float] = {}
    for hour_of_day, values in hour_values.items():
        if values:
            hourly_pattern[hour_of_day] = sum(values) / len(values)

    return hourly_pattern


def build_forecast_from_pattern(
    hourly_pattern: dict[int, float],
    forecast_times: Sequence[float],
    timezone: tzinfo | None = None,
) -> list[float]:
    """Build forecast values for the given timestamps based on hourly pattern.

    For each forecast time, returns the average value for that hour-of-day
    from the historical pattern.

    Args:
        hourly_pattern: Dictionary mapping hour-of-day (0-23) to average value
        forecast_times: List of timestamps to generate forecast for
        timezone: Timezone for hour-of-day calculation

    Returns:
        List of forecast values aligned to forecast_times (n_periods = len - 1)

    """
    if not forecast_times or len(forecast_times) < _MIN_FORECAST_TIMES:
        return []

    if not hourly_pattern:
        return [0.0] * (len(forecast_times) - 1)

    tz = timezone or dt_util.get_default_time_zone()

    # Generate values for each interval (n_periods = len(forecast_times) - 1)
    result: list[float] = []
    for i in range(len(forecast_times) - 1):
        # Use the start of each interval to determine the hour
        timestamp = forecast_times[i]
        dt = datetime.fromtimestamp(timestamp, tz=tz)
        hour_of_day = dt.hour

        # Get the pattern value for this hour, default to 0
        value = hourly_pattern.get(hour_of_day, 0.0)
        result.append(value)

    return result


async def build_forecast_from_history(
    hass: HomeAssistant,
    entity_id: str,
    forecast_times: Sequence[float],
    history_days: int = DEFAULT_HISTORY_DAYS,
) -> ForecastSeries:
    """Build a forecast time series from a sensor's historical statistics.

    Fetches the last `history_days` of hourly statistics for the sensor,
    builds a 24-hour pattern by averaging values for each hour-of-day,
    and projects that pattern forward as a forecast.

    Args:
        hass: Home Assistant instance
        entity_id: Sensor entity ID to fetch history for
        forecast_times: Timestamps for the forecast horizon
        history_days: Number of days of history to use

    Returns:
        ForecastSeries: List of (timestamp, value) tuples for the forecast

    """
    if not forecast_times:
        return []

    # Calculate time range for history
    now = dt_util.now()
    start_time = now - timedelta(days=history_days)
    start_time = start_time.replace(minute=0, second=0, microsecond=0)
    end_time = now.replace(minute=0, second=0, microsecond=0)

    # Fetch statistics
    statistics = await get_statistics_for_sensor(hass, entity_id, start_time, end_time)

    if not statistics:
        _LOGGER.warning("No historical statistics found for %s", entity_id)
        return []

    # Build hourly pattern from history
    hourly_pattern = build_hourly_pattern(statistics)

    if not hourly_pattern:
        _LOGGER.warning("Could not build hourly pattern from statistics for %s", entity_id)
        return []

    # Build forecast series from pattern
    tz = dt_util.get_default_time_zone()
    forecast: ForecastSeries = []

    for timestamp in forecast_times:
        dt_obj = datetime.fromtimestamp(timestamp, tz=tz)
        hour_of_day = dt_obj.hour
        value = hourly_pattern.get(hour_of_day, 0.0)
        forecast.append((timestamp, value))

    return forecast


class HistoricalForecastLoader:
    """Loader that builds forecasts from sensor historical statistics.

    When a sensor doesn't have a forecast attribute, this loader fetches
    historical data and creates a forecast based on the average pattern
    for each hour of the day.
    """

    def __init__(self, history_days: int = DEFAULT_HISTORY_DAYS) -> None:
        """Initialize the loader.

        Args:
            history_days: Number of days of history to fetch and use for forecast

        """
        self._history_days = history_days

    def available(self, *, hass: HomeAssistant, value: Any, **_kwargs: Any) -> bool:
        """Check if we can load data for the given sensor.

        Args:
            hass: Home Assistant instance
            value: Sensor entity ID or list of entity IDs

        Returns:
            True if the recorder component is available and sensors exist

        """
        # Check recorder is available
        if "recorder" not in hass.config.components:
            return False

        # Get entity IDs
        entity_ids = self._normalize_entity_ids(value)
        if not entity_ids:
            return False

        # Check all sensors exist
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
        """Load historical data and build a forecast.

        Args:
            hass: Home Assistant instance
            value: Sensor entity ID or list of entity IDs
            forecast_times: Timestamps for the forecast horizon

        Returns:
            List of power values aligned to forecast_times

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

        # Fetch and combine statistics from all sensors
        combined_pattern: dict[int, list[float]] = {h: [] for h in range(24)}

        for entity_id in entity_ids:
            try:
                statistics = await get_statistics_for_sensor(hass, entity_id, start_time, end_time)
            except ValueError as e:
                _LOGGER.warning("Failed to get statistics for %s: %s", entity_id, e)
                continue

            if not statistics:
                _LOGGER.debug("No statistics found for %s", entity_id)
                continue

            # Build pattern for this sensor using HA timezone
            tz = dt_util.get_default_time_zone()
            pattern = build_hourly_pattern(statistics, timezone=tz)

            # Add to combined pattern (will sum multiple sensors)
            for hour, value_avg in pattern.items():
                combined_pattern[hour].append(value_avg)

        # Sum the averages from each sensor for each hour
        hourly_pattern: dict[int, float] = {}
        for hour, values in combined_pattern.items():
            if values:
                hourly_pattern[hour] = sum(values)

        if not hourly_pattern:
            msg = f"No historical data available for sensors: {entity_ids}"
            raise ValueError(msg)

        # Build forecast from pattern
        return build_forecast_from_pattern(
            hourly_pattern,
            forecast_times,
            timezone=dt_util.get_default_time_zone(),
        )


# Keep backward compatibility alias
HistoricalLoadLoader = HistoricalForecastLoader
