"""Shared fixtures for adapter element tests."""

from collections.abc import Sequence
from typing import Any, Final

from homeassistant.core import HomeAssistant

FORECAST_TIMES: Final[Sequence[float]] = (0.0, 1800.0)


def set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


def set_forecast_sensor(
    hass: HomeAssistant,
    entity_id: str,
    value: str,
    forecast: list[dict[str, Any]],
    unit: str = "kW",
) -> None:
    """Set a sensor state with forecast attribute in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit, "forecast": forecast})
