"""Tests for HAEO system health reporting."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, Mock

from homeassistant.components.system_health import SystemHealthRegistration
from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.const import (
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    DEFAULT_TIER_1_COUNT,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_2_COUNT,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_COUNT,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_COUNT,
    DEFAULT_TIER_4_DURATION,
    OUTPUT_NAME_OPTIMIZATION_COST,
    OUTPUT_NAME_OPTIMIZATION_DURATION,
    OUTPUT_NAME_OPTIMIZATION_STATUS,
)
from custom_components.haeo.coordinator import CoordinatorOutput, HaeoDataUpdateCoordinator
from custom_components.haeo.model.const import OUTPUT_TYPE_COST, OUTPUT_TYPE_DURATION, OUTPUT_TYPE_STATUS
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
    coordinator.last_update_success_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    coordinator.data = {
        "HAEO Hub": {
            OUTPUT_NAME_OPTIMIZATION_STATUS: CoordinatorOutput(
                type=OUTPUT_TYPE_STATUS, unit=None, state="success", forecast=None
            ),
            OUTPUT_NAME_OPTIMIZATION_COST: CoordinatorOutput(
                type=OUTPUT_TYPE_COST, unit="$", state=42.75, forecast=None
            ),
            OUTPUT_NAME_OPTIMIZATION_DURATION: CoordinatorOutput(
                type=OUTPUT_TYPE_DURATION, unit="s", state=1.234, forecast=None
            ),
        },
        "Battery": {"soc": CoordinatorOutput(type=OUTPUT_TYPE_STATUS, unit=None, state=50, forecast=None)},
    }

    entry = MagicMock()
    entry.title = "HAEO Hub"
    entry.data = {
        CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
        CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
        CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
        CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
        CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
        CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
        CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
        CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
    }
    entry.runtime_data = coordinator

    hass.config_entries.async_entries = MagicMock(return_value=[entry])

    info = await async_system_health_info(hass)

    assert info["HAEO Hub_status"] == "ok"
    assert info["HAEO Hub_optimization_status"] == "success"
    assert info["HAEO Hub_last_optimization_cost"] == "42.75"
    assert info["HAEO Hub_last_optimization_duration"] == pytest.approx(1.234)
    assert info["HAEO Hub_last_optimization_time"] == "2024-01-01T12:00:00+00:00"
    assert info["HAEO Hub_outputs"] == 1
    # Check the tier-based configuration is reported
    total_periods = DEFAULT_TIER_1_COUNT + DEFAULT_TIER_2_COUNT + DEFAULT_TIER_3_COUNT + DEFAULT_TIER_4_COUNT
    assert info["HAEO Hub_total_periods"] == total_periods


async def test_system_health_detects_failed_updates(hass: HomeAssistant) -> None:
    """Failed coordinator updates are surfaced as update_failed."""

    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.last_update_success = False
    coordinator.data = {}
    coordinator.last_update_success_time = None

    entry = MagicMock()
    entry.title = "HAEO Hub"
    entry.data = {}
    entry.runtime_data = coordinator

    hass.config_entries.async_entries = MagicMock(return_value=[entry])

    info = await async_system_health_info(hass)

    assert info["HAEO Hub_status"] == "update_failed"
    assert info["HAEO Hub_outputs"] == 0
