"""Loader for unified time series sensor and forecast data."""

from collections.abc import Mapping, Sequence
import logging
from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.haeo.data.util.forecast_combiner import combine_sensor_payloads
from custom_components.haeo.data.util.forecast_fuser import fuse_to_horizon

from .historical_load_loader import HistoricalForecastLoader
from .sensor_loader import load_sensors, normalize_entity_ids

_LOGGER = logging.getLogger(__name__)


def _collect_sensor_ids(value: Any) -> list[str]:
    """Return all sensor entity IDs referenced by *value*."""

    if isinstance(value, Mapping):
        entity_ids: list[str] = []
        for sensors in value.values():
            if sensors is None:
                continue
            entity_ids.extend(normalize_entity_ids(sensors))
        return entity_ids

    return normalize_entity_ids(value)


class TimeSeriesLoader:
    """Loader that merges live sensor values and forecasts into a horizon-aligned time series.

    When sensors don't have forecast data, automatically falls back to building
    a forecast from historical statistics.
    """

    def available(self, *, hass: HomeAssistant, value: Any, **_kwargs: Any) -> bool:
        """Return True when every referenced sensor can supply data."""

        try:
            entity_ids = _collect_sensor_ids(value)
        except TypeError:
            return False

        if not entity_ids:
            return False

        payloads = load_sensors(hass, entity_ids)

        return len(payloads) == len(entity_ids)

    async def load(
        self,
        *,
        hass: HomeAssistant,
        value: Any,
        forecast_times: Sequence[float],
        **_kwargs: Any,
    ) -> list[float]:
        """Load sensor values and forecasts, returning interpolated values for ``forecast_times``.

        When forecast_times is empty, returns an empty list without loading sensor data.
        This allows structural validation and model element creation without requiring
        actual sensor data to be available.

        If sensors don't have forecast data (only present values), automatically
        falls back to building a forecast from historical recorder statistics.
        """

        entity_ids = _collect_sensor_ids(value)

        if not forecast_times:
            return []

        if not entity_ids:
            msg = "At least one sensor entity is required"
            raise ValueError(msg)

        payloads = load_sensors(hass, entity_ids)

        if not payloads:
            msg = "No time series data available"
            raise ValueError(msg)

        if len(payloads) < len(entity_ids):
            missing = set(entity_ids) - set(payloads.keys())
            msg = f"Sensors not found or unavailable: {', '.join(missing)}"
            raise ValueError(msg)

        present_value, forecast_series = combine_sensor_payloads(payloads)

        # If no forecast data available (only present values), use historical data
        if not forecast_series:
            _LOGGER.debug(
                "No forecast data for sensors %s, using historical statistics",
                entity_ids,
            )
            return await self._load_from_history(hass, entity_ids, forecast_times)

        return fuse_to_horizon(present_value, forecast_series, forecast_times)

    async def _load_from_history(
        self,
        hass: HomeAssistant,
        entity_ids: list[str],
        forecast_times: Sequence[float],
    ) -> list[float]:
        """Load forecast from historical statistics when no forecast data is available.

        Args:
            hass: Home Assistant instance
            entity_ids: List of sensor entity IDs to fetch history for
            forecast_times: Timestamps for the forecast horizon

        Returns:
            List of values for each forecast interval based on historical patterns

        """
        historical_loader = HistoricalForecastLoader()

        try:
            return await historical_loader.load(
                hass=hass,
                value=entity_ids,
                forecast_times=forecast_times,
            )
        except ValueError as e:
            _LOGGER.warning(
                "Failed to load historical data for %s: %s. Using present value.",
                entity_ids,
                e,
            )
            # Fall back to loading sensors and using just the present value
            payloads = load_sensors(hass, entity_ids)
            present_value, forecast_series = combine_sensor_payloads(payloads)
            return fuse_to_horizon(present_value, forecast_series, forecast_times)
