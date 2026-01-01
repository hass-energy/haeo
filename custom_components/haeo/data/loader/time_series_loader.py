"""Loader for unified time series sensor and forecast data."""

from collections.abc import Mapping, Sequence
from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.haeo.data.util.forecast_combiner import combine_sensor_payloads
from custom_components.haeo.data.util.forecast_fuser import fuse_to_horizon

from .sensor_loader import load_sensors, normalize_entity_ids


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

    async def load(
        self,
        *,
        hass: HomeAssistant,
        value: Any,
        forecast_times: Sequence[float],
        **_kwargs: Any,
    ) -> list[float]:
        """Load sensor values and forecasts, returning interpolated values for ``forecast_times``.

        Constant values (int/float) are broadcast to all forecast times.

        When forecast_times is empty, returns an empty list without loading sensor data.
        This allows structural validation and model element creation without requiring
        actual sensor data to be available.
        """
        if not forecast_times:
            return []

        # Handle constant values by broadcasting to all periods.
        # forecast_times are fence posts, so there are len - 1 periods.
        if _is_constant_value(value):
            n_periods = max(0, len(forecast_times) - 1)
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

        return fuse_to_horizon(present_value, forecast_series, forecast_times)
