"""Loader for historical load data from Home Assistant Energy Dashboard.

This loader calculates total household consumption using the formula:
    Total Load = Grid Import + Solar Production - Grid Export

This accounts for:
- Power drawn from the grid
- Solar power consumed locally (production minus what was exported)
"""

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
import logging
from typing import Any, TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.haeo.data.util import ForecastSeries
from custom_components.haeo.data.util.forecast_fuser import fuse_to_horizon

_LOGGER = logging.getLogger(__name__)

# Default number of days of history to use for forecast
DEFAULT_HISTORY_DAYS = 7


class EnergyEntities(TypedDict):
    """Categorized energy entity IDs from the Energy Dashboard."""

    grid_import: list[str]
    grid_export: list[str]
    solar: list[str]


async def get_energy_entities(hass: HomeAssistant) -> EnergyEntities:
    """Get categorized energy entity IDs from the Energy Dashboard configuration.

    Extracts from the Energy Manager:
    - Grid sources → flow_from → stat_energy_from (imports)
    - Grid sources → flow_to → stat_energy_to (exports)
    - Solar sources → stat_energy_from (production)

    Returns:
        Dictionary with categorized entity lists:
        {
            "grid_import": ["sensor.grid_import_energy"],
            "grid_export": ["sensor.grid_export_energy"],
            "solar": ["sensor.solar_production_energy"],
        }

    Raises:
        ValueError: If the Energy Dashboard is not configured
    """
    # Import energy manager from Home Assistant
    try:
        from homeassistant.components.energy.data import async_get_manager
    except ImportError as e:
        msg = "Energy component not available"
        raise ValueError(msg) from e

    manager = await async_get_manager(hass)
    if manager is None:
        msg = "Energy Dashboard not configured"
        raise ValueError(msg)

    prefs = manager.data
    if prefs is None:
        msg = "Energy Dashboard not configured"
        raise ValueError(msg)

    result: EnergyEntities = {
        "grid_import": [],
        "grid_export": [],
        "solar": [],
    }

    # Extract grid sources
    energy_sources = prefs.get("energy_sources", [])
    for source in energy_sources:
        source_type = source.get("type")

        if source_type == "grid":
            # Grid import: flow_from entries
            for flow_from in source.get("flow_from", []):
                stat_id = flow_from.get("stat_energy_from")
                if stat_id:
                    result["grid_import"].append(stat_id)

            # Grid export: flow_to entries
            for flow_to in source.get("flow_to", []):
                stat_id = flow_to.get("stat_energy_to")
                if stat_id:
                    result["grid_export"].append(stat_id)

        elif source_type == "solar":
            # Solar production
            stat_id = source.get("stat_energy_from")
            if stat_id:
                result["solar"].append(stat_id)

    return result


async def _get_statistics(
    hass: HomeAssistant,
    entity_ids: list[str],
    start_time: datetime,
    end_time: datetime,
) -> dict[str, list[dict[str, Any]]]:
    """Fetch hourly statistics for the given entity IDs.

    Returns:
        Dictionary mapping entity_id to list of statistics rows.
        Each row has 'start', 'end', 'mean', 'sum', etc.
    """
    if not entity_ids:
        return {}

    try:
        from homeassistant.components.recorder.statistics import (
            statistics_during_period,
        )
    except ImportError as e:
        msg = "Recorder component not available"
        raise ValueError(msg) from e

    # Fetch statistics - runs in executor since it's blocking
    statistics = await hass.async_add_executor_job(
        statistics_during_period,
        hass,
        start_time,
        end_time,
        set(entity_ids),
        "hour",  # period
        None,  # units - use native
        {"mean", "change"},  # types to fetch
    )

    return statistics


def build_forecast_from_history(
    statistics: dict[str, list[dict[str, Any]]],
    history_days: int,
    current_time: datetime,
) -> ForecastSeries:
    """Build a forecast time series from historical statistics.

    Calculates total consumption for each hour using:
        total_load = grid_import + solar_production - grid_export

    The history is then shifted forward to create a forecast for the next
    `history_days` days.

    Args:
        statistics: Dictionary mapping category names to statistics rows.
                   Categories are: "grid_import", "grid_export", "solar"
        history_days: Number of days of history used
        current_time: Current time to base the forecast on

    Returns:
        ForecastSeries: List of (timestamp, value) tuples representing
                       the forecasted load in watts (or the original unit).
    """
    # Collect all unique hour timestamps across all statistics
    all_hours: set[datetime] = set()

    for stats_list in statistics.values():
        for stat in stats_list:
            start = stat.get("start")
            if isinstance(start, datetime):
                all_hours.add(start)

    if not all_hours:
        return []

    # Build lookup tables for quick access
    # Using 'change' for energy sensors (kWh per hour)
    grid_import_by_hour: dict[datetime, float] = {}
    grid_export_by_hour: dict[datetime, float] = {}
    solar_by_hour: dict[datetime, float] = {}

    for stat in statistics.get("grid_import", []):
        start = stat.get("start")
        change = stat.get("change")
        if isinstance(start, datetime) and change is not None:
            grid_import_by_hour[start] = float(change)

    for stat in statistics.get("grid_export", []):
        start = stat.get("start")
        change = stat.get("change")
        if isinstance(start, datetime) and change is not None:
            grid_export_by_hour[start] = float(change)

    for stat in statistics.get("solar", []):
        start = stat.get("start")
        change = stat.get("change")
        if isinstance(start, datetime) and change is not None:
            solar_by_hour[start] = float(change)

    # Calculate total load for each hour
    # Formula: total_load = grid_import + solar_production - grid_export
    hourly_load: dict[datetime, float] = {}

    for hour in sorted(all_hours):
        grid_import = grid_import_by_hour.get(hour, 0.0)
        grid_export = grid_export_by_hour.get(hour, 0.0)
        solar = solar_by_hour.get(hour, 0.0)

        # Total consumption = what we bought + what we generated - what we sold
        total = grid_import + solar - grid_export
        # Ensure non-negative (shouldn't happen but safety check)
        hourly_load[hour] = max(0.0, total)

    # Create forecast by shifting historical hours forward
    # Each historical hour becomes a forecast for the same time-of-day in the future
    forecast: ForecastSeries = []
    shift_days = timedelta(days=history_days)

    for hour in sorted(hourly_load.keys()):
        future_time = hour + shift_days
        # Only include hours that are in the future relative to current time
        if future_time >= current_time:
            # Convert datetime to timestamp and value to watts (energy/hour = power)
            # Since statistics are in kWh per hour, this gives us kW average power
            timestamp = future_time.timestamp()
            value = hourly_load[hour]  # kWh per hour = kW
            forecast.append((timestamp, value))

    return forecast


class HistoricalLoadLoader:
    """Loader that builds load forecast from Energy Dashboard historical data.

    Uses the formula:
        Total Load = Grid Import + Solar Production - Grid Export
    """

    def __init__(self, history_days: int = DEFAULT_HISTORY_DAYS) -> None:
        """Initialize the loader.

        Args:
            history_days: Number of days of history to fetch and use for forecast
        """
        self._history_days = history_days

    def available(self, *, hass: HomeAssistant, **_kwargs: Any) -> bool:
        """Check if the Energy Dashboard is configured and has required data.

        Note: This is a synchronous check that only verifies the energy component
        is loaded. Full availability is checked during load().
        """
        # Check if energy component is available
        return "energy" in hass.config.components

    async def load(
        self,
        *,
        hass: HomeAssistant,
        forecast_times: Sequence[float],
        **_kwargs: Any,
    ) -> list[float]:
        """Load historical data and build a consumption forecast.

        Returns:
            List of power values (kW) aligned to forecast_times
        """
        if not forecast_times:
            return []

        # Get energy entities from the Energy Dashboard
        try:
            energy_entities = await get_energy_entities(hass)
        except ValueError as e:
            _LOGGER.warning("Cannot load historical data: %s", e)
            raise

        # Check if we have at least grid import data
        if not energy_entities["grid_import"]:
            msg = "No grid import entities configured in Energy Dashboard"
            raise ValueError(msg)

        # Calculate time range for history
        now = dt_util.now()
        start_time = now - timedelta(days=self._history_days)
        # Round to start of hour
        start_time = start_time.replace(minute=0, second=0, microsecond=0)
        end_time = now.replace(minute=0, second=0, microsecond=0)

        # Fetch statistics for all entity categories
        all_entity_ids = (
            energy_entities["grid_import"]
            + energy_entities["grid_export"]
            + energy_entities["solar"]
        )

        raw_statistics = await _get_statistics(hass, all_entity_ids, start_time, end_time)

        # Reorganize statistics by category
        categorized_stats: dict[str, list[dict[str, Any]]] = {
            "grid_import": [],
            "grid_export": [],
            "solar": [],
        }

        # Sum up statistics for each category if there are multiple entities
        for entity_id in energy_entities["grid_import"]:
            if entity_id in raw_statistics:
                categorized_stats["grid_import"].extend(raw_statistics[entity_id])

        for entity_id in energy_entities["grid_export"]:
            if entity_id in raw_statistics:
                categorized_stats["grid_export"].extend(raw_statistics[entity_id])

        for entity_id in energy_entities["solar"]:
            if entity_id in raw_statistics:
                categorized_stats["solar"].extend(raw_statistics[entity_id])

        # Aggregate multiple entities per category by summing values for the same hour
        for category in categorized_stats:
            stats_list = categorized_stats[category]
            if not stats_list:
                continue

            # Group by start time and sum the change values
            by_hour: dict[datetime, float] = {}
            for stat in stats_list:
                start = stat.get("start")
                change = stat.get("change")
                if isinstance(start, datetime) and change is not None:
                    by_hour[start] = by_hour.get(start, 0.0) + float(change)

            # Rebuild stats list with aggregated values
            categorized_stats[category] = [
                {"start": hour, "change": value}
                for hour, value in by_hour.items()
            ]

        # Build forecast from the categorized statistics
        forecast_series = build_forecast_from_history(
            categorized_stats,
            self._history_days,
            now,
        )

        if not forecast_series:
            msg = "No historical data available to build forecast"
            raise ValueError(msg)

        # Get current value (most recent hour's load)
        # Find the most recent historical hour that's before now
        current_value: float | None = None
        current_hour = now.replace(minute=0, second=0, microsecond=0)

        # Sum up the most recent hour's consumption from raw stats
        latest_grid_import = 0.0
        latest_grid_export = 0.0
        latest_solar = 0.0

        for stat in categorized_stats.get("grid_import", []):
            if stat.get("start") == current_hour:
                latest_grid_import += stat.get("change", 0.0)

        for stat in categorized_stats.get("grid_export", []):
            if stat.get("start") == current_hour:
                latest_grid_export += stat.get("change", 0.0)

        for stat in categorized_stats.get("solar", []):
            if stat.get("start") == current_hour:
                latest_solar += stat.get("change", 0.0)

        if latest_grid_import > 0 or latest_solar > 0:
            current_value = max(0.0, latest_grid_import + latest_solar - latest_grid_export)

        # Use fuse_to_horizon to align forecast to requested times
        return fuse_to_horizon(current_value, forecast_series, forecast_times)
