"""Tests for top-level migration orchestration."""

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import migrations
from custom_components.haeo.const import DOMAIN


async def test_async_migrate_entry_returns_false_when_step_fails(hass: HomeAssistant) -> None:
    """Orchestrator stops and reports failure when a migration handler returns False."""
    entry = MockConfigEntry(domain=DOMAIN, version=1, minor_version=0, data={})
    entry.add_to_hass(hass)

    async def failing_handler(*_args: object) -> bool:
        return False

    with patch.object(
        migrations,
        "MIGRATIONS",
        ((migrations.v1_3.MINOR_VERSION, failing_handler),),
    ):
        assert await migrations.async_migrate_entry(hass, entry) is False
