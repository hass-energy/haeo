"""Loader for `sensor` field types."""

from collections.abc import Sequence
from typing import Any, TypeGuard

from homeassistant.core import HomeAssistant

from custom_components.haeo.const import convert_to_base_unit


class SensorLoader:
    """Loader for sensor values (returns float)."""

    def available(self, *, hass: HomeAssistant, value: Any, **_kwargs: Any) -> bool:
        """Return True if all sensors are available.

        Args:
            hass: Home Assistant instance
            value: Single sensor entity ID or list of sensor entity IDs to check
            **_kwargs: Additional keyword arguments (unused)

        Returns:
            True if all sensors are available and have valid states

        """
        if not self.is_valid_value(value):
            msg = "Value must be a sensor ID (str) or sequence of sensor IDs"
            raise TypeError(msg)

        # Handle both single sensor ID (str) and list of sensor IDs (Sequence[str])
        sensor_list = [value] if isinstance(value, str) else list(value)

        return all(
            (state := hass.states.get(sid)) is not None and state.state not in ("unknown", "unavailable", "none")
            for sid in sensor_list
        )

    async def load(self, *, hass: HomeAssistant, value: Any, **_kwargs: Any) -> float:
        """Load sensor values and return their sum or single value.

        Args:
            hass: Home Assistant instance
            value: Single sensor entity ID or list of sensor entity IDs to load
            **kwargs: Additional keyword arguments (unused)

        Returns:
            Sum of all sensor values as a float (or single value if only one sensor)

        """
        if not self.is_valid_value(value):
            msg = "Value must be a sensor ID (str) or sequence of sensor IDs"
            raise TypeError(msg)

        # Handle both single sensor ID (str) and list of sensor IDs (Sequence[str])
        sensor_list: Sequence[str] = [value] if isinstance(value, str) else value

        total: float = 0.0
        for sid in sensor_list:
            state = hass.states.get(sid)
            if state is None:
                msg = f"Sensor {sid} not found"
                raise ValueError(msg)
            try:
                sensor_value = float(state.state)
            except (ValueError, TypeError) as e:
                msg = f"Cannot parse sensor value for {sid}: {state.state}"
                raise ValueError(msg) from e
            # Convert units when possible
            device_class = state.attributes.get("device_class")
            unit = state.attributes.get("unit_of_measurement")
            sensor_value = convert_to_base_unit(sensor_value, unit, device_class)
            total += sensor_value

        # Return the calculated total
        return total

    def is_valid_value(self, value: Any) -> TypeGuard[Sequence[str] | str]:
        """Check if the value is a valid sensor ID or sequence of sensor IDs."""
        return isinstance(value, str) or (isinstance(value, Sequence) and all(isinstance(item, str) for item in value))
