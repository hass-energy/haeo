"""Config entry migrations for HAEO."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import v1_3
from . import v1_4

type MigrationHandler = Callable[[HomeAssistant, ConfigEntry], Awaitable[bool]]

MIGRATIONS: tuple[tuple[int, MigrationHandler], ...] = (
    (v1_3.MINOR_VERSION, v1_3.async_migrate_entry),
    (v1_4.MINOR_VERSION, v1_4.async_migrate_entry),
)

MIGRATION_MINOR_VERSION = MIGRATIONS[-1][0] if MIGRATIONS else 0


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Run migrations for a config entry."""
    if entry.version != 1:
        return True

    for target_minor, handler in MIGRATIONS:
        if entry.minor_version < target_minor and not await handler(hass, entry):
            return False

    return True
