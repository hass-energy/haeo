"""Diagnostics support for HAEO integration."""

from homeassistant.core import HomeAssistant

from custom_components.haeo import HaeoConfigEntry

from .collector import DIAGNOSTICS_SCHEMA_VERSION, DiagnosticsResult, EnvironmentInfo, collect_diagnostics


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
) -> dict[str, object]:
    """Return diagnostics for a HAEO config entry.

    This is the Home Assistant entry point for diagnostics (current, not historical).
    """
    result = await collect_diagnostics(hass, config_entry)
    return result.to_dict()


__all__ = [
    "DIAGNOSTICS_SCHEMA_VERSION",
    "DiagnosticsResult",
    "EnvironmentInfo",
    "async_get_config_entry_diagnostics",
    "collect_diagnostics",
]
