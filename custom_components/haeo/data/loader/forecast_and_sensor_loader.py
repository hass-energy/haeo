"""Loader for mixed live+forecast price/power fields."""

from collections.abc import Sequence
from typing import Any, TypedDict, TypeGuard

from homeassistant.core import HomeAssistant

from .forecast_loader import ForecastLoader
from .sensor_loader import SensorLoader


class ForecastAndSensorValue(TypedDict):
    """Combined forecast and sensor value structure."""

    live: Sequence[str]
    forecast: Sequence[str]


class ForecastAndSensorLoader:
    """Loader for combined forecast + sensor data (returns list[float])."""

    def __init__(self) -> None:
        """Initialize with sensor and forecast loader instances."""
        self._sensor_loader = SensorLoader()
        self._forecast_loader = ForecastLoader()

    def available(self, *, hass: HomeAssistant, value: ForecastAndSensorValue, **kwargs: Any) -> bool:
        """Check if both live sensors and forecast sensors are available.

        Args:
            hass: Home Assistant instance
            value: Dictionary containing 'live' and 'forecast' sensor lists
            **kwargs: Additional keyword arguments

        Returns:
            True if both live and forecast sensors are available

        """
        sensors_available = self._sensor_loader.available(hass=hass, value=value["live"], **kwargs)
        forecasts_available = self._forecast_loader.available(hass=hass, value=value["forecast"], **kwargs)

        return sensors_available and forecasts_available

    async def load(self, *, hass: HomeAssistant, value: ForecastAndSensorValue, **kwargs: Any) -> list[float]:
        """Load forecast and sensor data for optimization.

        Args:
            hass: Home Assistant instance
            value: Dictionary containing 'live' and 'forecast' sensor lists
            forecast_times: Time intervals for data aggregation
            **kwargs: Additional keyword arguments

        Returns:
            List of forecast values with the first value replaced by live sensor data

        """
        live = await self._sensor_loader.load(hass=hass, value=value["live"], **kwargs)
        forecast = await self._forecast_loader.load(hass=hass, value=value["forecast"], **kwargs)

        forecast[0] = live

        return forecast

    def is_valid_value(self, value: object) -> TypeGuard[ForecastAndSensorValue]:
        """Check if value is a valid mapping with required keys and correctly typed values.

        ForecastAndSensorValue requires both 'live' and 'forecast' to be Sequence[str],
        not just any value accepted by the loaders (e.g., SensorLoader also accepts str).
        """
        if not isinstance(value, dict):
            return False
        if "live" not in value or "forecast" not in value:
            return False
        # Validate that both values are Sequence[str] as per TypedDict definition
        return self._forecast_loader.is_valid_value(value["live"]) and self._forecast_loader.is_valid_value(
            value["forecast"]
        )
