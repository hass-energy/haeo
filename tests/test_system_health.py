"""Tests for HAEO system health reporting."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, Mock, patch

from homeassistant.components.system_health import SystemHealthRegistration
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
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
from custom_components.haeo.coordinator import (
    CoordinatorData,
    CoordinatorOutput,
    HaeoDataUpdateCoordinator,
    OptimizationContext,
)
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.system_health import async_register, async_system_health_info


def _make_coordinator_data(outputs: dict[str, Any]) -> CoordinatorData:
    """Create a CoordinatorData instance for tests."""
    context = OptimizationContext(
        hub_config={},
        horizon_start=datetime.fromtimestamp(1000.0, tz=dt_util.UTC),
        participants={},
        source_states={},
    )
    return CoordinatorData(
        context=context,
        outputs=outputs,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


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

    with patch.object(hass.config_entries, "async_entries", return_value=[entry]):
        info = await async_system_health_info(hass)
    assert info["HAEO Hub_status"] == "coordinator_not_initialized"


async def test_system_health_reports_coordinator_state(hass: HomeAssistant) -> None:
    """System health surfaces coordinator metadata and configuration."""

    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.last_update_success = True
    coordinator.last_update_success_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    coordinator.data = _make_coordinator_data(
        {
            "HAEO Hub": {
                OUTPUT_NAME_OPTIMIZATION_STATUS: CoordinatorOutput(
                    type=OutputType.STATUS, unit=None, state="success", forecast=None
                ),
                OUTPUT_NAME_OPTIMIZATION_COST: CoordinatorOutput(
                    type=OutputType.COST, unit="$", state=42.75, forecast=None
                ),
                OUTPUT_NAME_OPTIMIZATION_DURATION: CoordinatorOutput(
                    type=OutputType.DURATION, unit="s", state=1.234, forecast=None
                ),
            },
            "Battery": {"soc": CoordinatorOutput(type=OutputType.STATUS, unit=None, state=50, forecast=None)},
        }
    )

    entry = MagicMock()
    entry.title = "HAEO Hub"
    entry.data = {
        CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
        CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
        CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
        CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
        CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
        CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
        CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
    }
    entry.runtime_data = coordinator

    with patch.object(hass.config_entries, "async_entries", return_value=[entry]):
        info = await async_system_health_info(hass)

    assert info["HAEO Hub_status"] == "ok"
    assert info["HAEO Hub_optimization_status"] == "success"
    assert info["HAEO Hub_last_optimization_cost"] == "42.75"
    assert info["HAEO Hub_last_optimization_duration"] == pytest.approx(1.234)
    assert info["HAEO Hub_last_optimization_time"] == "2024-01-01T12:00:00+00:00"
    assert info["HAEO Hub_outputs"] == 1
    # Check the tier-based configuration is reported (110 periods with default config)
    assert info["HAEO Hub_total_periods"] == 110


async def test_system_health_detects_failed_updates(hass: HomeAssistant) -> None:
    """Failed coordinator updates are surfaced as update_failed."""

    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.last_update_success = False
    coordinator.data = _make_coordinator_data({})
    coordinator.last_update_success_time = None

    entry = MagicMock()
    entry.title = "HAEO Hub"
    entry.data = {
        CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
        CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
        CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
        CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
        CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
        CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
        CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
    }
    entry.runtime_data = coordinator

    with patch.object(hass.config_entries, "async_entries", return_value=[entry]):
        info = await async_system_health_info(hass)

    assert info["HAEO Hub_status"] == "update_failed"
    assert info["HAEO Hub_outputs"] == 0
