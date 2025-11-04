"""Loader for forecast-only fields."""

from collections.abc import Sequence
from typing import Any, TypeGuard

from homeassistant.core import HomeAssistant
import numpy as np

from custom_components.haeo.const import convert_to_base_unit

from .forecast_parsers import detect_format, get_forecast_units, parse_forecast_data


class ForecastLoader:
    """Loader for forecast data (returns list[float])."""

    def available(self, *, hass: HomeAssistant, value: Any, **_kwargs: Any) -> bool:
        """Check if forecast sensors are available and contain valid forecast data.

        Args:
            hass: Home Assistant instance
            value: List of sensor entity IDs
            **_kwargs: Additional keyword arguments (unused)

        Returns:
            True if all sensors are available and contain forecast data

        """
        return self.is_valid_value(value) and all(
            (state := hass.states.get(entity_id)) is not None
            and state.state not in ("unknown", "unavailable", "none")
            and detect_format(state) is not None
            for entity_id in value
        )

    async def load(
        self, *, hass: HomeAssistant, value: Any, forecast_times: Sequence[int], **_kwargs: Any
    ) -> list[float]:
        """Load forecast data from sensors and aggregate into time buckets.

        Args:
            hass: Home Assistant instance
            value: List of sensor entity IDs
            forecast_times: Time intervals for data aggregation
            **_kwargs: Additional keyword arguments (unused)

        Returns:
            List of aggregated forecast values for each time bucket

        """
        if not self.is_valid_value(value):
            msg = "Value must be a sequence of sensor entity IDs (strings)"
            raise TypeError(msg)

        # Gather all the series data from the sensors grouped into forecast_times buckets
        output = np.zeros(len(forecast_times))
        for entity_id in value:
            state = hass.states.get(entity_id)
            if state is None:
                msg = f"Sensor {entity_id} not found"
                raise ValueError(msg)

            # Try to parse forecast data first
            forecast_data = parse_forecast_data(state)
            if forecast_data is not None:
                # Get units from the forecast parser (not from sensor attributes)
                unit, device_class = get_forecast_units(state)

                # Convert forecast values to base units (kW, kWh, etc.)
                # device_class may be a SensorDeviceClass or None
                converted_forecast = [
                    (timestamp, convert_to_base_unit(value, unit, device_class)) for timestamp, value in forecast_data
                ]

                # Use forecast data if available
                data = np.array(converted_forecast, dtype=[("timestamp", np.int64), ("value", np.float64)])
                output += np.interp(forecast_times, data["timestamp"], data["value"], left=0, right=0)
            else:
                # No forecast data available for this sensor
                msg = f"No forecast data available for sensor {entity_id}"
                raise ValueError(msg)

        return output.tolist()

    def is_valid_value(self, value: Any) -> TypeGuard[Sequence[str]]:
        """Check if the value is a valid sequence of strings."""

        # Note: str is a Sequence in Python, but we need a sequence OF strings, not a string.
        return (
            isinstance(value, Sequence) and not isinstance(value, str) and all(isinstance(item, str) for item in value)
        )
