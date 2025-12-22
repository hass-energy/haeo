"""Loader for unified time series sensor and forecast data."""

from collections.abc import Mapping, Sequence
from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.haeo.data.util.forecast_combiner import combine_sensor_payloads
from custom_components.haeo.data.util.forecast_fuser import fuse_to_horizon

from .sensor_loader import load_sensors, normalize_entity_ids


def _is_constant_value(value: Any) -> bool:
    """Return True if value is a constant number (not a sensor reference)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _collect_sensor_ids(value: Any) -> list[str]:
    """Return all sensor entity IDs referenced by *value*.

    Returns an empty list if value is a constant number.
    """
    # Constant values have no sensor IDs to collect
    if _is_constant_value(value):
        return []

    if isinstance(value, Mapping):
        entity_ids: list[str] = []
        for sensors in value.values():
            if sensors is None:
                continue
            if _is_constant_value(sensors):
                continue
            entity_ids.extend(normalize_entity_ids(sensors))
        return entity_ids

    return normalize_entity_ids(value)


class TimeSeriesLoader:
    """Loader that merges live sensor values and forecasts into a horizon-aligned time series."""

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
    ) -> list[float] | None:
        """Load sensor values and forecasts, returning interpolated values for ``forecast_times``.

        When forecast_times is empty, returns an empty list without loading sensor data.
        This allows structural validation and model element creation without requiring
        actual sensor data to be available.

        When a constant numeric value is provided, returns that value repeated for each
        forecast time. This enables fields to accept either sensor entity IDs or direct
        numeric values.

        When no entity IDs are provided (empty list or None), returns None to signal
        that this field should use its default/fallback behavior.
        """
        # Handle constant numeric values
        if _is_constant_value(value):
            if not forecast_times:
                return []
            return [float(value)] * len(forecast_times)

        entity_ids = _collect_sensor_ids(value)

        if not forecast_times:
            return []

        if not entity_ids:
            # No sensors provided - return None to signal fallback behavior
            return None

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
