"""Loader for mixed live+forecast price/power fields."""

from collections.abc import Sequence
from typing import Any, Literal

from homeassistant.core import HomeAssistant

from . import forecast_loader, sensor_loader


# --------------------------------------------------------------
def available(
    hass: HomeAssistant, field_value: dict[Literal["live", "forecast"], Sequence[str]], **kwargs: Any
) -> bool:
    sensors = field_value.get("live")
    forecasts = field_value.get("forecast")

    # Check if sensors are available (they should exist and have valid states)
    sensors_available = sensor_loader.available(hass, sensors, **kwargs)
    # Check if forecasts are available (they should exist and have valid states or forecast data)
    forecasts_available = forecast_loader.available(hass, forecasts, **kwargs)

    return sensors_available and forecasts_available


async def load(
    hass: HomeAssistant,
    field_value: dict[Literal["live", "forecast"], Sequence[str]],
    *,
    forecast_times: Sequence[int],
    **kwargs: Any,
):
    live = await sensor_loader.load(hass, field_value.get("live"), **kwargs)
    forecast = await forecast_loader.load(hass, field_value.get("forecast"), forecast_times=forecast_times, **kwargs)

    if live is None or forecast is None:
        msg = "Live or forecast data is missing"
        raise ValueError(msg)

    forecast[0] = live

    return forecast
