"""Loader for scalar (non-forecast) sensor values."""

from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.haeo.core.units import normalize_measurement
from custom_components.haeo.schema import EntityValue

from .sensor_loader import normalize_entity_ids


class ScalarLoader:
    """Loader that reads current sensor state without forecasting."""

    def available(self, *, hass: HomeAssistant, value: EntityValue, **_kwargs: Any) -> bool:
        """Return True when every referenced sensor has a usable state."""
        entity_ids = value["value"]
        if not entity_ids:
            return False

        try:
            normalized = normalize_entity_ids(entity_ids)
        except TypeError:
            return False

        for entity_id in normalized:
            state = hass.states.get(entity_id)
            if state is None:
                return False
            if (
                _coerce_state_value(
                    state.state,
                    state.attributes.get("unit_of_measurement"),
                    state.attributes.get("device_class"),
                )
                is None
            ):
                return False

        return True

    async def load(self, *, hass: HomeAssistant, value: EntityValue, **_kwargs: Any) -> float:
        """Load current scalar values and return the sum.

        Raises:
            ValueError: If any referenced sensor is unavailable or invalid.

        """
        entity_ids = value["value"]
        if not entity_ids:
            msg = "At least one sensor entity is required"
            raise ValueError(msg)

        normalized = normalize_entity_ids(entity_ids)
        total = 0.0
        for entity_id in normalized:
            state = hass.states.get(entity_id)
            if state is None:
                msg = f"Sensor {entity_id} not found or unavailable"
                raise ValueError(msg)
            value_float = _coerce_state_value(
                state.state,
                state.attributes.get("unit_of_measurement"),
                state.attributes.get("device_class"),
            )
            if value_float is None:
                msg = f"Sensor {entity_id} has no numeric state"
                raise ValueError(msg)
            total += value_float

        return total


def _coerce_state_value(state_value: Any, unit: str | None, device_class: str | None) -> float | None:
    """Return the numeric state value converted to base units."""
    try:
        value = float(state_value)
    except (TypeError, ValueError):
        return None

    normalized_value, _, _ = normalize_measurement(value, unit, device_class)
    return normalized_value


__all__ = ["ScalarLoader"]
