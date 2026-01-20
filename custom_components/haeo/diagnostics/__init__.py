"""Diagnostics support for HAEO integration."""

from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.haeo import HaeoConfigEntry

from .collector import collect_diagnostics
from .historical_state_provider import HistoricalStateProvider
from .state_provider import CurrentStateProvider, StateProvider


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a HAEO config entry.

    This is the Home Assistant entry point for diagnostics.
    It delegates to collect_diagnostics with a CurrentStateProvider.
    """
    return await collect_diagnostics(hass, config_entry, CurrentStateProvider(hass))


__all__ = [
    "CurrentStateProvider",
    "HistoricalStateProvider",
    "StateProvider",
    "async_get_config_entry_diagnostics",
    "collect_diagnostics",
]
