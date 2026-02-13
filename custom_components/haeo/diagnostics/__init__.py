"""Diagnostics support for HAEO integration."""

from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.haeo import HaeoConfigEntry

from .collector import DiagnosticsInfo, DiagnosticsResult, EnvironmentInfo, collect_diagnostics
from .historical_state_provider import HistoricalStateProvider
from .state_provider import CurrentStateProvider, StateProvider


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a HAEO config entry.

    This is the Home Assistant entry point for diagnostics (current, not historical).
    """
    result = await collect_diagnostics(hass, config_entry)
    return result.to_dict()


__all__ = [
    "CurrentStateProvider",
    "DiagnosticsInfo",
    "DiagnosticsResult",
    "EnvironmentInfo",
    "HistoricalStateProvider",
    "StateProvider",
    "async_get_config_entry_diagnostics",
    "collect_diagnostics",
]
