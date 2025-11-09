"""Loader for unified time series sensor and forecast data."""

from collections.abc import Mapping, Sequence
from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.haeo.data.util.forecast_combiner import combine_sensor_payloads

from .fusion import fuse_to_horizon
from .sensor_loader import load_sensors, normalize_entity_ids


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
        forecast_times: Sequence[int],
        **_kwargs: Any,
    ) -> list[float]:
        """Load sensor values and forecasts, returning a time series aligned to ``forecast_times``."""

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

        return fuse_to_horizon(present_value, forecast_series, forecast_times)
