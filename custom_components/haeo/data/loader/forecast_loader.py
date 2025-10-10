"""Loader for forecast-only fields."""

from collections.abc import Sequence
from typing import Any

from homeassistant.core import HomeAssistant
import numpy as np

from .forecast_parsers import detect_format, parse_forecast_data


def available(*, hass: HomeAssistant, value: Sequence[str], **_kwargs: Any) -> bool:
    """Check if forecast sensors are available and contain valid forecast data.

    Args:
        hass: Home Assistant instance
        value: List of sensor entity IDs
        **_kwargs: Additional keyword arguments (unused)

    Returns:
        True if all sensors are available and contain forecast data

    """
    return all(
        (state := hass.states.get(entity_id)) is not None
        and state.state not in ("unknown", "unavailable", "none")
        and detect_format(state) is not None
        for entity_id in value
    )


async def load(
    *, hass: HomeAssistant, value: Sequence[str], forecast_times: Sequence[int], **_kwargs: Any
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
            # Use forecast data if available
            data = np.array(forecast_data, dtype=[("timestamp", np.int64), ("value", np.float64)])
            output += np.interp(forecast_times, data["timestamp"], data["value"], left=0, right=0)
        else:
            # No forecast data available for this sensor
            msg = f"No forecast data available for sensor {entity_id}"
            raise ValueError(msg)

    return output.tolist()
