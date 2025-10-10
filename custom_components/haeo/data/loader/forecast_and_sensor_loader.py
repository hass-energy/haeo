"""Loader for mixed live+forecast price/power fields."""

from collections.abc import Sequence
from typing import Any, Literal

from homeassistant.core import HomeAssistant

from . import forecast_loader, sensor_loader


# --------------------------------------------------------------
def available(
    *, hass: HomeAssistant, field_value: dict[Literal["live", "forecast"], Sequence[str]], **_kwargs: Any
) -> bool:
    """Check if both live sensors and forecast sensors are available.

    Args:
        hass: Home Assistant instance
        field_value: Dictionary containing 'live' and 'forecast' sensor lists
        **_kwargs: Additional keyword arguments (unused)

    Returns:
        True if both live and forecast sensors are available

    """
    sensors = field_value.get("live")
    forecasts = field_value.get("forecast")

    # Check if sensors are available (they should exist and have valid states)
    sensors_available = sensor_loader.available(hass, sensors)
    # Check if forecasts are available (they should exist and have valid states or forecast data)
    forecasts_available = forecast_loader.available(hass, forecasts)

    return sensors_available and forecasts_available


async def load(
    *,
    hass: HomeAssistant,
    field_value: dict[Literal["live", "forecast"], Sequence[str]],
    forecast_times: Sequence[int],
    **_kwargs: Any,
) -> list[float]:
    """Load forecast and sensor data for optimization."""
    live = await sensor_loader.load(hass, field_value.get("live"))
    forecast = await forecast_loader.load(hass, field_value.get("forecast"), forecast_times=forecast_times)

    if live is None or forecast is None:
        msg = "Live or forecast data is missing"
        raise ValueError(msg)

    forecast[0] = live

    return forecast
