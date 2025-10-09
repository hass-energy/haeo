"""Loader for `sensor` field types."""

from collections.abc import Sequence
from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.haeo.const import convert_to_base_unit


def available(hass: HomeAssistant, sensors: Sequence[str], **_kwargs: Any) -> bool:
    """Return True if all sensors are available.

    Args:
        hass: Home Assistant instance
        sensors: List of sensor entity IDs to check
        **_kwargs: Additional keyword arguments (unused)

    Returns:
        True if all sensors are available and have valid states

    """
    return all(
        hass.states.get(sid) is not None and hass.states.get(sid).state not in ("unknown", "unavailable", "none")
        for sid in sensors
    )


async def load(hass: HomeAssistant, sensors: Sequence[str], **_kwargs: Any) -> float:
    """Load sensor values and return their sum.

    Args:
        hass: Home Assistant instance
        sensors: List of sensor entity IDs to load
        **_kwargs: Additional keyword arguments (unused)

    Returns:
        Sum of all sensor values as a float

    """
    total: float = 0.0
    for sid in sensors:
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
    return total
