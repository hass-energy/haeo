"""Loader for `sensor` field types."""

from collections.abc import Sequence
from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.haeo.const import convert_to_base_unit


def available(*, hass: HomeAssistant, value: str | Sequence[str], **_kwargs: Any) -> bool:
    """Return True if all sensors are available.

    Args:
        hass: Home Assistant instance
        sensors: Single sensor entity ID or list of sensor entity IDs to check
        **_kwargs: Additional keyword arguments (unused)

    Returns:
        True if all sensors are available and have valid states

    """
    # Handle both single sensor ID (str) and list of sensor IDs (Sequence[str])
    sensor_list = [value] if isinstance(value, str) else list(value)

    return all(
        hass.states.get(sid) is not None and hass.states.get(sid).state not in ("unknown", "unavailable", "none")
        for sid in sensor_list
    )


async def load(*, hass: HomeAssistant, value: str | Sequence[str], **_kwargs: Any) -> float:
    """Load sensor values and return their sum or single value.

    Args:
        hass: Home Assistant instance
        value: Single sensor entity ID or list of sensor entity IDs to load
        **_kwargs: Additional keyword arguments (unused)

    Returns:
        Sum of all sensor values as a float (or single value if only one sensor)

    """
    # Handle both single sensor ID (str) and list of sensor IDs (Sequence[str])
    sensor_list: Sequence[str] = [value] if isinstance(value, str) else value

    total: float = 0.0
    for sid in sensor_list:
        state = hass.states.get(sid)
        if state is None:
            msg = f"Sensor {sid} not found"
            raise ValueError(msg)
        try:
            value = float(state.state)
        except (ValueError, TypeError) as e:
            msg = f"Cannot parse sensor value for {sid}: {state.state}"
            raise ValueError(msg) from e
        # Convert units when possible
        device_class = state.attributes.get("device_class")
        unit = state.attributes.get("unit_of_measurement")
        value = convert_to_base_unit(value, unit, device_class)
        total += value

    # Return the calculated total
    return total
