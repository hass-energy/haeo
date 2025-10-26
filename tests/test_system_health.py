"""Tests for HAEO system health reporting."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, Mock

from homeassistant.components.system_health import SystemHealthRegistration
from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.const import CONF_HORIZON_HOURS, CONF_OPTIMIZER, CONF_PERIOD_MINUTES
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.system_health import async_register, async_system_health_info


async def test_async_register_callback(hass: HomeAssistant) -> None:
    """The system health callback is registered."""

    registration = MagicMock(spec=SystemHealthRegistration)
    async_register(hass, registration)
    registration.async_register_info.assert_called_once_with(async_system_health_info)


async def test_system_health_no_config_entries(hass: HomeAssistant) -> None:
    """When no config entries exist a simple status is returned."""

    info = await async_system_health_info(hass)
    assert info == {"status": "no_config_entries"}


async def test_system_health_coordinator_not_initialized(hass: HomeAssistant) -> None:
    """Entries without runtime data are identified explicitly."""

    entry = MagicMock()
    entry.title = "HAEO Hub"
    entry.runtime_data = None

    hass.config_entries.async_entries = MagicMock(return_value=[entry])

    info = await async_system_health_info(hass)
    assert info["HAEO Hub_status"] == "coordinator_not_initialized"


async def test_system_health_reports_coordinator_state(hass: HomeAssistant) -> None:
    """System health surfaces coordinator metadata and configuration."""

    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.last_update_success = True
    coordinator.optimization_status = "success"
    coordinator.last_optimization_cost = 42.75
    coordinator.last_optimization_duration = 1.234
    coordinator.last_optimization_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    coordinator.data = {"battery": {"soc": object()}}
    coordinator.config = {
        CONF_OPTIMIZER: "highs",
        CONF_HORIZON_HOURS: 48,
        CONF_PERIOD_MINUTES: 10,
    }

    entry = MagicMock()
    entry.title = "HAEO Hub"
    entry.runtime_data = coordinator

    hass.config_entries.async_entries = MagicMock(return_value=[entry])

    info = await async_system_health_info(hass)

    assert info["HAEO Hub_status"] == "ok"
    assert info["HAEO Hub_optimization_status"] == "success"
    assert info["HAEO Hub_last_optimization_cost"] == "42.75"
    assert info["HAEO Hub_last_optimization_duration"] == pytest.approx(1.234)
    assert info["HAEO Hub_last_optimization_time"] == "2024-01-01T12:00:00+00:00"
    assert info["HAEO Hub_outputs"] == 1
    assert info["HAEO Hub_optimizer"] == "highs"
    assert info["HAEO Hub_horizon_hours"] == 48
    assert info["HAEO Hub_period_minutes"] == 10


async def test_system_health_detects_failed_updates(hass: HomeAssistant) -> None:
    """Failed coordinator updates are surfaced as update_failed."""

    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.last_update_success = False
    coordinator.optimization_status = "pending"
    coordinator.last_optimization_cost = None
    coordinator.last_optimization_duration = None
    coordinator.last_optimization_time = None
    coordinator.data = {}
    coordinator.config = {}

    entry = MagicMock()
    entry.title = "HAEO Hub"
    entry.runtime_data = coordinator

    hass.config_entries.async_entries = MagicMock(return_value=[entry])

    info = await async_system_health_info(hass)

    assert info["HAEO Hub_status"] == "update_failed"
    assert info["HAEO Hub_outputs"] == 0
