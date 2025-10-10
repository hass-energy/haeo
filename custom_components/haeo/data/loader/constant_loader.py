"""Loader for constant (scalar) configuration values."""

from typing import Any


def available(**_kwargs: Any) -> bool:
    """Return True if the constant field is available.

    Args:
        _hass: Home Assistant instance (unused for constants)
        _field_value: The constant field value (unused for availability check)
        **_kwargs: Additional keyword arguments (unused)

    Returns:
        True always, as constants are always available

    """
    return True  # Constants are always available


async def load(*, value: Any, **_kwargs: Any) -> Any:
    """Load the constant field value.

    Args:
        _hass: Home Assistant instance (unused for constants)
        field_value: The constant field value to return
        **_kwargs: Additional keyword arguments (unused)

    Returns:
        The constant field value

    """
    return value
