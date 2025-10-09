"""Loader for constant (scalar) configuration values."""

from typing import Any

from homeassistant.core import HomeAssistant


def available(hass: HomeAssistant, field_value: Any, **_kwargs: Any) -> bool:
    """Return True if the constant field is available.

    Args:
        hass: Home Assistant instance (unused for constants)
        field_value: The constant field value (unused for availability check)
        **_kwargs: Additional keyword arguments (unused)

    Returns:
        True always, as constants are always available

    """
    return True  # Constants are always available


async def load(hass: HomeAssistant, field_value: Any, **_kwargs: Any) -> Any:
    """Load the constant field value.

    Args:
        _hass: Home Assistant instance (unused for constants)
        field_value: The constant field value to return
        **_kwargs: Additional keyword arguments (unused)

    Returns:
        The constant field value

    """
    return field_value
