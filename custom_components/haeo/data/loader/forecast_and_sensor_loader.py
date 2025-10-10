"""Loader for mixed live+forecast price/power fields."""

from collections.abc import Sequence
from typing import Any, Literal

from homeassistant.core import HomeAssistant

from . import forecast_loader, sensor_loader


def available(*, hass: HomeAssistant, value: dict[Literal["live", "forecast"], Sequence[str]], **_kwargs: Any) -> bool:
    """Check if both live sensors and forecast sensors are available.

    Args:
        hass: Home Assistant instance
        value: Dictionary containing 'live' and 'forecast' sensor lists
        **_kwargs: Additional keyword arguments (unused)

    Returns:
        True if both live and forecast sensors are available

    """
    sensors = value.get("live")
    forecasts = value.get("forecast")

    if sensors is None or forecasts is None:
        return False

    # Check if sensors are available (they should exist and have valid states)
    sensors_available = sensor_loader.available(hass=hass, value=sensors)
    # Check if forecasts are available (they should exist and have valid states or forecast data)
    forecasts_available = forecast_loader.available(hass=hass, value=forecasts)

    return sensors_available and forecasts_available


async def load(
    *,
    hass: HomeAssistant,
    value: dict[Literal["live", "forecast"], Sequence[str]],
    forecast_times: Sequence[int],
    **_kwargs: Any,
) -> list[float]:
    """Load forecast and sensor data for optimization."""
    live_sensors = value.get("live")
    forecast_sensors = value.get("forecast")

    if live_sensors is None or forecast_sensors is None:
        msg = "Live or forecast data is missing"
        raise ValueError(msg)

    live = await sensor_loader.load(hass=hass, value=live_sensors)
    forecast = await forecast_loader.load(hass=hass, value=forecast_sensors, forecast_times=forecast_times)

    forecast[0] = live

    return forecast
