"""Tests for HAEO system health reporting."""

from datetime import UTC, datetime

# Coordinator output fixtures use runtime string keys that cannot satisfy the
# Literal key types of SubentryDevices.
from typing import Any  # noqa: TID251
from unittest.mock import MagicMock, Mock, patch

from homeassistant.components.system_health import SystemHealthRegistration
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
import pytest

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import OUTPUT_NAME_OPTIMIZATION_COST, OUTPUT_NAME_OPTIMIZATION_DURATION
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


def _make_runtime_data(coordinator: HaeoDataUpdateCoordinator | None) -> HaeoRuntimeData:
    """Create runtime data for system health tests."""
    return HaeoRuntimeData(horizon_manager=Mock(periods_seconds=[300] * 12 + [3600] * 23), coordinator=coordinator)


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


async def test_system_health_runtime_data_without_coordinator(
    hass: HomeAssistant,
) -> None:
    """Runtime data without a coordinator is identified explicitly."""

    entry = MagicMock()
    entry.title = "HAEO Hub"
    entry.runtime_data = _make_runtime_data(coordinator=None)

    with patch.object(hass.config_entries, "async_entries", return_value=[entry]):
        info = await async_system_health_info(hass)
    assert info["HAEO Hub_status"] == "coordinator_not_initialized"


async def test_system_health_reports_coordinator_state(hass: HomeAssistant) -> None:
    """System health surfaces coordinator metadata and configuration."""

    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.last_update_success = True
    coordinator.optimization_status = "success"
    coordinator.last_update_success_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    coordinator.data = _make_coordinator_data(
        {
            "HAEO Hub": {
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
    entry.runtime_data = _make_runtime_data(coordinator)

    with patch.object(hass.config_entries, "async_entries", return_value=[entry]):
        info = await async_system_health_info(hass)

    assert info["HAEO Hub_status"] == "ok"
    assert info["HAEO Hub_optimization_status"] == "success"
    assert info["HAEO Hub_last_optimization_cost"] == "42.75"
    assert info["HAEO Hub_last_optimization_duration"] == pytest.approx(1.234)
    assert info["HAEO Hub_last_optimization_time"] == "2024-01-01T12:00:00+00:00"
    assert info["HAEO Hub_outputs"] == 1
    assert info["HAEO Hub_total_periods"] == 35
    assert info["HAEO Hub_horizon_minutes"] == 1440


async def test_system_health_detects_failed_updates(hass: HomeAssistant) -> None:
    """Failed coordinator updates are surfaced as update_failed."""

    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.last_update_success = False
    coordinator.optimization_status = "failed"
    coordinator.data = _make_coordinator_data({})
    coordinator.last_update_success_time = None

    entry = MagicMock()
    entry.title = "HAEO Hub"
    entry.runtime_data = _make_runtime_data(coordinator)

    with patch.object(hass.config_entries, "async_entries", return_value=[entry]):
        info = await async_system_health_info(hass)

    assert info["HAEO Hub_status"] == "update_failed"
    assert info["HAEO Hub_optimization_status"] == "failed"
    assert info["HAEO Hub_outputs"] == 0
