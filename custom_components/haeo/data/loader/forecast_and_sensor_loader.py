"""Loader for mixed live+forecast price/power fields."""

from collections.abc import Mapping, Sequence
from typing import Any, Literal, TypeGuard

from homeassistant.core import HomeAssistant

from .forecast_loader import ForecastLoader
from .sensor_loader import SensorLoader


class ForecastAndSensorLoader:
    """Loader for combined forecast + sensor data (returns list[float])."""

    Keys = Literal["live", "forecast"]

    def __init__(self) -> None:
        """Initialize with sensor and forecast loader instances."""
        self._sensor_loader = SensorLoader()
        self._forecast_loader = ForecastLoader()

    def available(self, *, hass: HomeAssistant, value: Any, **kwargs: Any) -> bool:
        """Check if both live sensors and forecast sensors are available.

        Args:
            hass: Home Assistant instance
            value: Dictionary containing 'live' and 'forecast' sensor lists
            **kwargs: Additional keyword arguments

        Returns:
            True if both live and forecast sensors are available

        """
        if not self.is_valid_value(value):
            msg = "Value must be a mapping"
            raise TypeError(msg)

        sensors = value.get("live")
        forecasts = value.get("forecast")

        if sensors is None or forecasts is None:
            return False

        # Check if sensors are available (they should exist and have valid states)
        sensors_available = self._sensor_loader.available(hass=hass, value=sensors, **kwargs)
        # Check if forecasts are available (they should exist and have valid states or forecast data)
        forecasts_available = self._forecast_loader.available(hass=hass, value=forecasts, **kwargs)

        return sensors_available and forecasts_available

    async def load(self, *, hass: HomeAssistant, value: Any, **kwargs: Any) -> list[float]:
        """Load forecast and sensor data for optimization.

        Args:
            hass: Home Assistant instance
            value: Dictionary containing 'live' and 'forecast' sensor lists
            forecast_times: Time intervals for data aggregation
            **kwargs: Additional keyword arguments

        Returns:
            List of forecast values with the first value replaced by live sensor data

        """
        if not self.is_valid_value(value):
            msg = "Value must be a mapping"
            raise TypeError(msg)

        live_sensors = value.get("live")
        forecast_sensors = value.get("forecast")

        if live_sensors is None or forecast_sensors is None:
            msg = "Live or forecast data is missing"
            raise ValueError(msg)

        live = await self._sensor_loader.load(hass=hass, value=live_sensors, **kwargs)
        forecast = await self._forecast_loader.load(hass=hass, value=forecast_sensors, **kwargs)

        forecast[0] = live

        return forecast

    def is_valid_value(self, value: Any) -> TypeGuard[Mapping[Keys, Sequence[str] | str]]:
        """Check if the value is a valid mapping with 'live' and 'forecast' keys."""
        if not isinstance(value, Mapping):
            return False
        live = value.get("live")
        forecast = value.get("forecast")

        is_live_valid = live is None or self._sensor_loader.is_valid_value(live)
        is_forecast_valid = forecast is None or self._forecast_loader.is_valid_value(forecast)
        return is_live_valid and is_forecast_valid
