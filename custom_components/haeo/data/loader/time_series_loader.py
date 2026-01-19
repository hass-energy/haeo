"""Loader for unified time series sensor and forecast data."""

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from homeassistant.core import HomeAssistant

from custom_components.haeo.data.util.forecast_combiner import combine_sensor_payloads
from custom_components.haeo.data.util.forecast_fuser import fuse_to_boundaries, fuse_to_intervals

from .sensor_loader import load_sensors, normalize_entity_ids

# Re-export interpolation mode type for callers
type InterpolationMode = Literal["linear", "step"]


def _is_constant_value(value: Any) -> bool:
    """Return True when value is a constant (int or float) rather than entity IDs."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _collect_sensor_ids(value: Any) -> list[str]:
    """Return all sensor entity IDs referenced by *value*.

    Callers must check for constant values (int/float) before calling this function.
    Raises TypeError for invalid input types.
    """
    if isinstance(value, Mapping):
        entity_ids: list[str] = []
        for sensors in value.values():
            if sensors is not None and not _is_constant_value(sensors):
                entity_ids.extend(normalize_entity_ids(sensors))
        return entity_ids

    return normalize_entity_ids(value)


class TimeSeriesLoader:
    """Loader that merges live sensor values and forecasts into a horizon-aligned time series."""

    def available(self, *, hass: HomeAssistant, value: Any, **_kwargs: Any) -> bool:
        """Return True when every referenced sensor can supply data.

        Constant values (int/float) are always available.
        """
        # Constant values are always available
        if _is_constant_value(value):
            return True

        try:
            entity_ids = _collect_sensor_ids(value)
        except TypeError:
            return False

        if not entity_ids:
            return False

        payloads = load_sensors(hass, entity_ids)

        return len(payloads) == len(entity_ids)

    async def load_intervals(
        self,
        *,
        hass: HomeAssistant,
        value: Any,
        forecast_times: Sequence[float],
        interpolation: InterpolationMode = "linear",
    ) -> list[float]:
        """Load a value as interval averages (n values for n+1 boundaries).

        Args:
            hass: Home Assistant instance
            value: Entity ID(s) or constant value (must not be None)
            forecast_times: Boundary timestamps (n+1 values defining n intervals)
            interpolation: How to interpolate between forecast points:
                - "linear": Values change linearly between points (power, efficiency)
                - "step": Values hold until the next point (prices)

        Returns:
            n interval values (averages over each period)

        Raises:
            ValueError: If value is None, empty, or sensors unavailable

        """
        if not forecast_times:
            return []

        n_periods = max(0, len(forecast_times) - 1)

        # Handle constant values by broadcasting to all periods
        if _is_constant_value(value):
            return [float(value)] * n_periods

        entity_ids = _collect_sensor_ids(value)

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

        return fuse_to_intervals(present_value, forecast_series, forecast_times, interpolation)

    async def load_boundaries(
        self,
        *,
        hass: HomeAssistant,
        value: Any,
        forecast_times: Sequence[float],
    ) -> list[float]:
        """Load a value as boundaries (n+1 point-in-time values).

        Args:
            hass: Home Assistant instance
            value: Entity ID(s) or constant value (must not be None)
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

        # Handle constant values by broadcasting to all boundaries
        if _is_constant_value(value):
            return [float(value)] * n_boundaries

        entity_ids = _collect_sensor_ids(value)

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
