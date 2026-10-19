"""Tests for HAEO system health reporting."""

from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock

from homeassistant.components.system_health import SystemHealthRegistration
from homeassistant.config_entries import ConfigEntryState, ConfigSubentryData
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoConfigEntry, HaeoRuntimeData
from custom_components.haeo.const import (
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
    NETWORK_DEVICE_NETWORK,
    OUTPUT_NAME_OPTIMIZATION_COST,
    OUTPUT_NAME_OPTIMIZATION_DURATION,
    OUTPUT_NAME_OPTIMIZATION_STATUS,
)
from custom_components.haeo.coordinator import (
    CoordinatorData,
    CoordinatorOutput,
    HaeoDataUpdateCoordinator,
    OptimizationContext,
    SubentryDevices,
)
from custom_components.haeo.core.adapters.elements.battery import (
    BATTERY_DEVICE_BATTERY,
    BATTERY_ENERGY_STORED,
    BATTERY_STATE_OF_CHARGE,
)
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.system_health import async_register, async_system_health_info

NETWORK_SUBENTRY_TITLE = "System"


def _make_entry(hass: HomeAssistant, state: ConfigEntryState = ConfigEntryState.LOADED) -> HaeoConfigEntry:
    """Create a HAEO hub entry with its network subentry, added to hass in the given state."""
    network_subentry = ConfigSubentryData(
        data={CONF_NAME: NETWORK_SUBENTRY_TITLE, CONF_ELEMENT_TYPE: ELEMENT_TYPE_NETWORK},
        subentry_type=ELEMENT_TYPE_NETWORK,
        title=NETWORK_SUBENTRY_TITLE,
        unique_id=None,
    )
    entry: HaeoConfigEntry = MockConfigEntry(
        domain=DOMAIN, title="HAEO Hub", state=state, subentries_data=[network_subentry]
    )
    entry.add_to_hass(hass)
    return entry


def _make_coordinator_data(outputs: dict[str, SubentryDevices]) -> CoordinatorData:
    """Create a CoordinatorData instance for tests."""
    context = OptimizationContext(
        hub_config={},
        horizon_start=datetime(2024, 1, 1, 11, 0, tzinfo=UTC),
        participants={},
        source_states={},
    )
    return CoordinatorData(
        context=context,
        outputs=outputs,
        started_at=datetime(2024, 1, 1, 11, 59, tzinfo=UTC),
        completed_at=datetime(2024, 1, 1, 23, 0, tzinfo=timezone(timedelta(hours=11))),
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


@pytest.mark.parametrize(
    "state",
    [ConfigEntryState.NOT_LOADED, ConfigEntryState.SETUP_RETRY, ConfigEntryState.SETUP_ERROR],
)
async def test_system_health_reports_unloaded_entry_state(hass: HomeAssistant, state: ConfigEntryState) -> None:
    """Entries that are not loaded report their state without reading runtime data."""

    _make_entry(hass, state)

    info = await async_system_health_info(hass)
    assert info == {"HAEO Hub_status": state.value}


async def test_system_health_coordinator_not_initialized(hass: HomeAssistant) -> None:
    """Loaded entries without runtime data are identified explicitly."""

    entry = _make_entry(hass)
    entry.runtime_data = None

    info = await async_system_health_info(hass)
    assert info == {"HAEO Hub_status": "coordinator_not_initialized"}


async def test_system_health_runtime_data_without_coordinator(hass: HomeAssistant) -> None:
    """Runtime data without a coordinator is identified explicitly."""

    entry = _make_entry(hass)
    entry.runtime_data = _make_runtime_data(coordinator=None)

    info = await async_system_health_info(hass)
    assert info == {"HAEO Hub_status": "coordinator_not_initialized"}


async def test_system_health_reports_coordinator_state(hass: HomeAssistant) -> None:
    """System health surfaces coordinator metadata and configuration."""

    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.last_update_success = True
    coordinator.data = _make_coordinator_data(
        {
            NETWORK_SUBENTRY_TITLE: {
                NETWORK_DEVICE_NETWORK: {
                    OUTPUT_NAME_OPTIMIZATION_STATUS: CoordinatorOutput(
                        type=OutputType.STATUS, unit=None, state="success", forecast=None
                    ),
                    OUTPUT_NAME_OPTIMIZATION_COST: CoordinatorOutput(
                        type=OutputType.COST, unit="$", state=42.75, forecast=None
                    ),
                    OUTPUT_NAME_OPTIMIZATION_DURATION: CoordinatorOutput(
                        type=OutputType.DURATION, unit="s", state=1.234, forecast=None
                    ),
                }
            },
            "Battery": {
                BATTERY_DEVICE_BATTERY: {
                    BATTERY_STATE_OF_CHARGE: CoordinatorOutput(
                        type=OutputType.STATE_OF_CHARGE, unit="%", state=50, forecast=None
                    ),
                    BATTERY_ENERGY_STORED: CoordinatorOutput(
                        type=OutputType.ENERGY, unit="kWh", state=5, forecast=None
                    ),
                },
            },
        }
    )

    entry = _make_entry(hass)
    entry.runtime_data = _make_runtime_data(coordinator)

    info = await async_system_health_info(hass)

    assert info == {
        "HAEO Hub_status": "ok",
        "HAEO Hub_optimization_status": "success",
        "HAEO Hub_last_optimization_cost": "42.75",
        "HAEO Hub_last_optimization_duration": pytest.approx(1.234),
        "HAEO Hub_last_optimization_time": "2024-01-01T12:00:00+00:00",
        "HAEO Hub_outputs": 2,
        "HAEO Hub_total_periods": 35,
        "HAEO Hub_horizon_minutes": 1440,
    }


async def test_system_health_detects_failed_updates(hass: HomeAssistant) -> None:
    """Failed coordinator updates without data are surfaced as update_failed with pending status."""

    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.last_update_success = False
    coordinator.data = None

    entry = _make_entry(hass)
    entry.runtime_data = _make_runtime_data(coordinator)

    info = await async_system_health_info(hass)

    assert info == {
        "HAEO Hub_status": "update_failed",
        "HAEO Hub_optimization_status": "pending",
        "HAEO Hub_outputs": 0,
        "HAEO Hub_total_periods": 35,
        "HAEO Hub_horizon_minutes": 1440,
    }
