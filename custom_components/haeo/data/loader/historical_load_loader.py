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


class EnergyEntities:
    """Categorized energy entities from the Energy dashboard."""

    def __init__(
        self,
        grid_import: list[str] | None = None,
        grid_export: list[str] | None = None,
        solar: list[str] | None = None,
    ) -> None:
        """Initialize energy entities."""
        self.grid_import: list[str] = grid_import or []
        self.grid_export: list[str] = grid_export or []
        self.solar: list[str] = solar or []

    def all_entity_ids(self) -> list[str]:
        """Return all entity IDs for fetching statistics."""
        return self.grid_import + self.grid_export + self.solar

    def has_entities(self) -> bool:
        """Return True if any entities are configured."""
        return bool(self.grid_import or self.grid_export or self.solar)


async def get_energy_entities(hass: HomeAssistant) -> EnergyEntities:
    """Get categorized energy entity IDs from the Energy dashboard configuration.

    Returns:
        EnergyEntities object containing categorized statistic IDs:
        - grid_import: Entities tracking energy imported from the grid
        - grid_export: Entities tracking energy exported to the grid
        - solar: Entities tracking solar production

    """
    # Import here to avoid issues if energy component not loaded
    try:
        from homeassistant.components.energy.data import async_get_manager  # noqa: PLC0415
    except ImportError:
        _LOGGER.warning("Energy component not available")
        return EnergyEntities()

    try:
        manager = await async_get_manager(hass)
        if manager.data is None:
            _LOGGER.warning("Energy manager has no data")
            return EnergyEntities()

        grid_import: list[str] = []
        grid_export: list[str] = []
        solar: list[str] = []

        # Extract entities from energy sources
        for source in manager.data.get("energy_sources", []):
            source_type = source.get("type")

            if source_type == "grid":
                # Grid sources have flow_from (import) and flow_to (export)
                for flow in source.get("flow_from", []):
                    stat_id = flow.get("stat_energy_from")
                    if stat_id:
                        grid_import.append(stat_id)

                for flow in source.get("flow_to", []):
                    stat_id = flow.get("stat_energy_to")
                    if stat_id:
                        grid_export.append(stat_id)

            elif source_type == "solar":
                # Solar sources have stat_energy_from for production
                stat_id = source.get("stat_energy_from")
                if stat_id:
                    solar.append(stat_id)

        return EnergyEntities(grid_import=grid_import, grid_export=grid_export, solar=solar)

    except Exception:
        _LOGGER.exception("Failed to get energy entities")
        return EnergyEntities()


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

    return await recorder.async_add_executor_job(
        statistics_during_period,
        hass,
        start_time,
        end_time,
        statistic_ids,
        "hour",
        {"energy": "kWh"},  # Convert all energy statistics to kWh
        {"change"},  # types - use "change" to get hourly energy deltas
    )


def _aggregate_statistics_by_timestamp(
    statistics: Mapping[str, Sequence[StatisticsRow]],
    entity_ids: list[str],
) -> dict[float, float]:
    """Aggregate statistics for given entity IDs by timestamp.

    Args:
        statistics: Dictionary of statistics from the recorder
        entity_ids: List of entity IDs to aggregate

    Returns:
        Dictionary mapping timestamps to summed energy values (kWh).

    """
    result: dict[float, float] = {}

    for entity_id in entity_ids:
        stat_list = statistics.get(entity_id, [])
        for stat in stat_list:
            start = stat.get("start")
            if start is None:
                continue

            timestamp = start.timestamp() if isinstance(start, datetime) else float(start)

            change = stat.get("change")
            if change is None:
                continue

            result[timestamp] = result.get(timestamp, 0.0) + float(change)

    return result


def build_forecast_from_history(
    statistics: Mapping[str, Sequence[StatisticsRow]],
    energy_entities: EnergyEntities,
    history_days: int,
) -> ForecastSeries:
    """Build a forecast series from historical statistics.

    Calculates total load using the formula:
        Total Load = Grid Import + Solar Production - Grid Export

    This accounts for:
    - Power drawn from the grid (grid import)
    - Solar power consumed locally (production minus export)

    Converts hourly energy (kWh) to average power (kW).
    The forecast timestamps are shifted forward by history_days to represent future predictions.

    Args:
        statistics: Dictionary of statistics from the recorder
        energy_entities: Categorized energy entities from the Energy dashboard
        history_days: Number of days of history (used to shift timestamps forward)

    Returns:
        Forecast series as list of (timestamp, power_kw) tuples.

    """
    if not statistics:
        return []

    # Aggregate statistics by category
    grid_import = _aggregate_statistics_by_timestamp(statistics, energy_entities.grid_import)
    grid_export = _aggregate_statistics_by_timestamp(statistics, energy_entities.grid_export)
    solar_production = _aggregate_statistics_by_timestamp(statistics, energy_entities.solar)

    # Get all unique timestamps
    all_timestamps = set(grid_import.keys()) | set(grid_export.keys()) | set(solar_production.keys())

    if not all_timestamps:
        return []

    # Calculate total load for each timestamp
    # Total Load = Grid Import + Solar Production - Grid Export
    hourly_power: dict[float, float] = {}
    for timestamp in all_timestamps:
        import_power = grid_import.get(timestamp, 0.0)
        export_power = grid_export.get(timestamp, 0.0)
        solar_power = solar_production.get(timestamp, 0.0)

        total_load = import_power + solar_power - export_power
        # Ensure non-negative (edge case protection)
        hourly_power[timestamp] = max(0.0, total_load)

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

    def available(self, *, hass: HomeAssistant, value: Any, **_kwargs: Any) -> bool:  # noqa: ARG002
        """Return True - we allow saving even if energy sensors aren't configured.

        Validation happens at load time when we actually try to fetch the data.
        """
        # Accept any integer value for history_days
        try:
            int(value)
        except (TypeError, ValueError):
            return False
        else:
            return True

    async def load(
        self,
        *,
        hass: HomeAssistant,
        value: Any,
        forecast_times: Sequence[float],
        **_kwargs: Any,
    ) -> list[float]:
        """Load historical consumption data and return interpolated values for forecast_times.

        Calculates total load from Energy dashboard entities using:
            Total Load = Grid Import + Solar Production - Grid Export

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

        # Get categorized energy entities from Energy dashboard
        energy_entities = await get_energy_entities(hass)
        _LOGGER.info(
            "Energy entities - grid_import: %s, grid_export: %s, solar: %s",
            energy_entities.grid_import,
            energy_entities.grid_export,
            energy_entities.solar,
        )
        if not energy_entities.has_entities():
            msg = (
                "No energy sensors configured in Home Assistant's Energy dashboard. "
                "Please configure energy sources in Settings → Dashboards → Energy, "
                "or use 'Custom Sensor' mode for the load forecast."
            )
            raise ValueError(msg)

        # Fetch historical statistics for all entity types
        all_entity_ids = energy_entities.all_entity_ids()
        statistics = await fetch_historical_statistics(hass, all_entity_ids, history_days)
        if not statistics:
            msg = (
                f"No historical data available for the past {history_days} days. "
                "Please ensure your energy sensors have been recording data."
            )
            raise ValueError(msg)

        # Log sample statistics for debugging
        for entity_id, stat_list in statistics.items():
            if stat_list:
                sample_values = [s.get("change") for s in stat_list[:5]]
                _LOGGER.info("Statistics for %s: first 5 values = %s", entity_id, sample_values)

        # Build forecast from historical data using total load calculation
        forecast_series = build_forecast_from_history(statistics, energy_entities, history_days)
        if not forecast_series:
            msg = "Failed to build forecast from historical data"
            raise ValueError(msg)

        # Log forecast summary
        if forecast_series:
            load_values = [v for _, v in forecast_series]
            _LOGGER.info(
                "Load forecast summary - min: %.2f kW, max: %.2f kW, avg: %.2f kW, count: %d",
                min(load_values),
                max(load_values),
                sum(load_values) / len(load_values),
                len(load_values),
            )
            # Log first few values
            _LOGGER.info("First 5 load values (kW): %s", load_values[:5])

        # Use the first value from the forecast as the present value
        # (since we're shifting historical data forward)
        present_value = forecast_series[0][1] if forecast_series else 0.0

        # Fuse to horizon - this handles cycling the forecast to cover the entire horizon
        return fuse_to_horizon(present_value, forecast_series, forecast_times)
