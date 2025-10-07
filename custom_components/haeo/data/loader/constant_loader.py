"""Loader for constant (scalar) configuration values."""

from typing import Any

from homeassistant.core import HomeAssistant


def available(hass: HomeAssistant, field_value: Any) -> bool:
    return True  # Constants are always available


async def load(hass: HomeAssistant, field_value: Any, **kwargs: Any) -> Any:
    return field_value
