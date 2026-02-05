"""Loader for unified time series sensor and forecast data."""

from collections.abc import Sequence
from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.haeo.data.util.forecast_combiner import combine_sensor_payloads
from custom_components.haeo.data.util.forecast_fuser import fuse_to_boundaries, fuse_to_intervals
from custom_components.haeo.schema import EntityValue

from .sensor_loader import load_sensors


class TimeSeriesLoader:
    """Loader that merges live sensor values and forecasts into a horizon-aligned time series."""

    def available(self, *, hass: HomeAssistant, value: EntityValue, **_kwargs: Any) -> bool:
        """Return True when every referenced sensor can supply data.
        """
        entity_ids = value["value"]

        if not entity_ids:
            return False

        payloads = load_sensors(hass, entity_ids)

        return len(payloads) == len(entity_ids)

    async def load_intervals(
        self,
        *,
        hass: HomeAssistant,
        value: EntityValue,
        forecast_times: Sequence[float],
    ) -> list[float]:
        """Load a value as interval averages (n values for n+1 boundaries).

        Args:
            hass: Home Assistant instance
            value: Entity schema value describing entities
            forecast_times: Boundary timestamps (n+1 values defining n intervals)

        Returns:
            n interval values (trapezoidal averages over each period)

        Raises:
            ValueError: If value is None, empty, or sensors unavailable

        """
        if not forecast_times:
            return []

        n_periods = max(0, len(forecast_times) - 1)

        entity_ids = value["value"]

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

        return fuse_to_intervals(present_value, forecast_series, forecast_times)

    async def load_boundaries(
        self,
        *,
        hass: HomeAssistant,
        value: EntityValue,
        forecast_times: Sequence[float],
    ) -> list[float]:
        """Load a value as boundaries (n+1 point-in-time values).

        Args:
            hass: Home Assistant instance
            value: Entity schema value describing entities
            forecast_times: Boundary timestamps (n+1 values defining n intervals)

        Returns:
            n+1 point-in-time values (one for each boundary)

        Use this for energy values (capacity, percentage limits) which represent
        states at specific points in time, not averages over intervals.

        Raises:
            ValueError: If value is None, empty, or sensors unavailable

        """
        if not forecast_times:
            return []

        n_boundaries = len(forecast_times)

        entity_ids = value["value"]

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

        return fuse_to_boundaries(present_value, forecast_series, forecast_times)
