"""Loader for historical consumption data from Home Assistant's Energy dashboard."""

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.recorder.statistics import StatisticsRow, statistics_during_period
from homeassistant.core import HomeAssistant
from homeassistant.helpers.recorder import get_instance
from homeassistant.util import dt as dt_util

from custom_components.haeo.data.util import ForecastSeries
from custom_components.haeo.data.util.forecast_fuser import fuse_to_horizon

_LOGGER = logging.getLogger(__name__)

# Seconds per hour for power calculations
_SECONDS_PER_HOUR = 3600


async def get_energy_consumption_entities(hass: HomeAssistant) -> list[str]:
    """Get consumption entity IDs from the Energy dashboard configuration.

    Returns:
        List of statistic IDs for grid consumption entities configured in the Energy dashboard.

    """
    # Import here to avoid issues if energy component not loaded
    try:
        from homeassistant.components.energy.data import async_get_manager  # noqa: PLC0415
    except ImportError:
        _LOGGER.warning("Energy component not available")
        return []

    try:
        manager = await async_get_manager(hass)
        if manager.data is None:
            _LOGGER.warning("Energy manager has no data")
            return []

        consumption_entities: list[str] = []

        # Extract consumption entities from grid energy sources
        for source in manager.data.get("energy_sources", []):
            if source.get("type") == "grid":
                # Grid sources have flow_from (consumption) and flow_to (export)
                for flow in source.get("flow_from", []):
                    stat_id = flow.get("stat_energy_from")
                    if stat_id:
                        consumption_entities.append(stat_id)

        return consumption_entities

    except Exception:
        _LOGGER.exception("Failed to get energy consumption entities")
        return []


async def fetch_historical_statistics(
    hass: HomeAssistant,
    statistic_ids: list[str],
    history_days: int,
) -> Mapping[str, list[StatisticsRow]]:
    """Fetch hourly statistics for the given statistic IDs.

    Args:
        hass: Home Assistant instance
        statistic_ids: List of statistic IDs to fetch
        history_days: Number of days of history to fetch

    Returns:
        Dictionary mapping statistic IDs to their hourly statistics.

    """
    if not statistic_ids:
        return {}

    now = dt_util.utcnow()
    # Round down to the start of the current hour
    end_time = now.replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(days=history_days)

    recorder = get_instance(hass)

    stats = await recorder.async_add_executor_job(
        statistics_during_period,
        hass,
        start_time,
        end_time,
        statistic_ids,
        "hour",
        None,  # units
        {"change"},  # types - use "change" to get hourly energy deltas
    )

    return stats


def build_forecast_from_history(
    statistics: Mapping[str, Sequence[StatisticsRow]],
    history_days: int,
) -> ForecastSeries:
    """Build a forecast series from historical statistics.

    Converts hourly energy consumption (kWh) to average power (kW).
    The forecast timestamps are shifted forward by history_days to represent future predictions.

    Args:
        statistics: Dictionary of statistics from the recorder
        history_days: Number of days of history (used to shift timestamps forward)

    Returns:
        Forecast series as list of (timestamp, power_kw) tuples.

    """
    if not statistics:
        return []

    # Combine all statistics into a single time series
    # First, collect all hourly data points by timestamp
    hourly_power: dict[float, float] = {}

    for stat_list in statistics.values():
        for stat in stat_list:
            # Get the timestamp (start of the hour)
            start = stat.get("start")
            if start is None:
                continue

            # Convert to timestamp if it's a datetime
            if isinstance(start, datetime):
                timestamp = start.timestamp()
            else:
                timestamp = float(start)

            # Get the energy change for this hour (kWh)
            # "change" represents the energy consumed during this hour
            change = stat.get("change")
            if change is None:
                continue

            # Convert energy (kWh) to average power (kW)
            # For hourly data, kWh / 1h = kW
            power_kw = float(change)

            # Sum power from all entities at this timestamp
            hourly_power[timestamp] = hourly_power.get(timestamp, 0.0) + power_kw

    if not hourly_power:
        return []

    # Sort by timestamp and shift forward by history_days
    shift_seconds = history_days * 24 * _SECONDS_PER_HOUR
    forecast: ForecastSeries = [(timestamp + shift_seconds, power) for timestamp, power in sorted(hourly_power.items())]

    return forecast


class HistoricalLoadLoader:
    """Loader that fetches historical consumption data from the Energy dashboard.

    This loader:
    1. Gets consumption entity IDs from the Energy Manager
    2. Fetches hourly statistics from the recorder
    3. Converts energy (kWh) to power (kW)
    4. Creates a forecast series that repeats throughout the optimization horizon
    """

    def available(self, *, hass: HomeAssistant, value: Any, **_kwargs: Any) -> bool:
        """Return True - we allow saving even if energy sensors aren't configured.

        Validation happens at load time when we actually try to fetch the data.
        """
        # Accept any integer value for history_days
        try:
            int(value)
            return True
        except (TypeError, ValueError):
            return False

    async def load(
        self,
        *,
        hass: HomeAssistant,
        value: Any,
        forecast_times: Sequence[float],
        **_kwargs: Any,
    ) -> list[float]:
        """Load historical consumption data and return interpolated values for forecast_times.

        Args:
            hass: Home Assistant instance
            value: Number of days of history to fetch
            forecast_times: Boundary timestamps for the optimization horizon

        Returns:
            List of power values (kW) aligned with forecast_times

        Raises:
            ValueError: If no consumption data is available

        """
        if not forecast_times:
            return []

        history_days = int(value)

        # Get consumption entities from Energy dashboard
        consumption_entities = await get_energy_consumption_entities(hass)
        if not consumption_entities:
            msg = (
                "No consumption sensors configured in Home Assistant's Energy dashboard. "
                "Please configure energy sources in Settings → Dashboards → Energy, "
                "or use 'Custom Sensor' mode for the load forecast."
            )
            raise ValueError(msg)

        # Fetch historical statistics
        statistics = await fetch_historical_statistics(hass, consumption_entities, history_days)
        if not statistics:
            msg = (
                f"No historical data available for the past {history_days} days. "
                "Please ensure your energy sensors have been recording data."
            )
            raise ValueError(msg)

        # Build forecast from historical data
        forecast_series = build_forecast_from_history(statistics, history_days)
        if not forecast_series:
            msg = "Failed to build forecast from historical data"
            raise ValueError(msg)

        # Use the first value from the forecast as the present value
        # (since we're shifting historical data forward)
        present_value = forecast_series[0][1] if forecast_series else 0.0

        # Fuse to horizon - this handles cycling the forecast to cover the entire horizon
        return fuse_to_horizon(present_value, forecast_series, forecast_times)
