"""Loader for forecast-only fields."""

from collections.abc import Sequence
from typing import Any

from homeassistant.core import HomeAssistant
import numpy as np

from .forecast_parsers import detect_format, parse_forecast_data


def available(hass: HomeAssistant, field_value: Sequence[str], **kwargs: Any) -> bool:
    return all(
        hass.states.get(entity_id) is not None
        and hass.states.get(entity_id).state not in ("unknown", "unavailable", "none")
        and detect_format(hass.states.get(entity_id)) is not None
        for entity_id in field_value
    )


async def load(
    hass: HomeAssistant, field_value: Sequence[str], *, forecast_times: Sequence[int], **kwargs: Any
) -> list[float]:
    # Gather all the series data from the sensors grouped into forecast_times buckets
    output = np.zeros(len(forecast_times))
    for entity_id in field_value:
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
            raise ValueError(f"No forecast data available for sensor {entity_id}")

    return output.tolist()
