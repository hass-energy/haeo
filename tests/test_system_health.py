"""Test system health integration."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from homeassistant.components.system_health import SystemHealthRegistration
from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.const import OPTIMIZATION_STATUS_PENDING, OPTIMIZATION_STATUS_SUCCESS
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.model import Network
from custom_components.haeo.system_health import async_register, async_system_health_info


async def test_async_register_callback(hass: HomeAssistant) -> None:
    """Test async_register registers the callback."""
    register = MagicMock(spec=SystemHealthRegistration)
    async_register(hass, register)
    register.async_register_info.assert_called_once_with(async_system_health_info)


async def test_system_health_no_config_entries(hass: HomeAssistant) -> None:
    """Test system health when no config entries exist."""
    health_info = await async_system_health_info(hass)
    assert health_info == {"status": "no_config_entries"}


async def test_system_health_coordinator_not_initialized(hass: HomeAssistant, config_entry: MagicMock) -> None:
    """Test system health when coordinator is not initialized."""
    config_entry.title = "Test Hub"
    config_entry.runtime_data = None
    hass.config_entries.async_entries = MagicMock(return_value=[config_entry])

    health_info = await async_system_health_info(hass)
    assert health_info["Test Hub_status"] == "coordinator_not_initialized"


async def test_system_health_network_not_built(
    hass: HomeAssistant, config_entry: MagicMock, coordinator: HaeoDataUpdateCoordinator
) -> None:
    """Test system health when network is not built."""
    config_entry.title = "Test Hub"
    config_entry.runtime_data = coordinator
    coordinator.network = None
    coordinator.optimization_status = OPTIMIZATION_STATUS_PENDING

    hass.config_entries.async_entries = MagicMock(return_value=[config_entry])

    health_info = await async_system_health_info(hass)
    assert health_info["Test Hub_network"] == "not_built"
    assert health_info["Test Hub_optimization_status"] == "pending"


async def test_system_health_valid_network(
    hass: HomeAssistant, config_entry: MagicMock, coordinator: HaeoDataUpdateCoordinator
) -> None:
    """Test system health with a valid network."""
    # Create a simple network
    network = Network(name="test_network", period=300 / 3600, n_periods=12)
    network.add("battery", "test_battery", capacity=10.0)

    config_entry.title = "Test Hub"
    config_entry.runtime_data = coordinator
    coordinator.network = network
    coordinator.optimization_status = OPTIMIZATION_STATUS_SUCCESS
    coordinator.optimization_result = {
        "cost": 12.34,
        "duration": 0.567,
        "timestamp": datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
    }

    hass.config_entries.async_entries = MagicMock(return_value=[config_entry])

    health_info = await async_system_health_info(hass)
    assert health_info["Test Hub_network"] == "valid"
    assert health_info["Test Hub_elements"] == 1
    assert health_info["Test Hub_connections"] == 0
    assert health_info["Test Hub_optimization_status"] == "success"
    assert health_info["Test Hub_last_optimization_cost"] == "12.34"
    assert health_info["Test Hub_last_optimization_duration"] == "0.567s"
    assert health_info["Test Hub_last_optimization_time"] == "2023-01-01T12:00:00+00:00"
    assert health_info["Test Hub_optimizer"] == "highs"
    assert health_info["Test Hub_horizon_hours"] == 24
    assert health_info["Test Hub_period_minutes"] == 5


async def test_system_health_unavailable_sensors(
    hass: HomeAssistant, config_entry: MagicMock, coordinator: HaeoDataUpdateCoordinator
) -> None:
    """Test system health reports unavailable sensors."""
    network = Network(name="test_network", period=300 / 3600, n_periods=12)
    config_entry.title = "Test Hub"
    config_entry.runtime_data = coordinator
    coordinator.network = network
    coordinator.optimization_status = OPTIMIZATION_STATUS_PENDING

    # Mock check_sensors_available to return unavailable sensors
    coordinator.check_sensors_available = MagicMock(
        return_value=(False, ["sensor.battery_soc", "sensor.grid_power", "sensor.solar_forecast"])
    )

    hass.config_entries.async_entries = MagicMock(return_value=[config_entry])

    health_info = await async_system_health_info(hass)
    assert health_info["Test Hub_sensors"] == "3_unavailable"
    assert "sensor.battery_soc" in health_info["Test Hub_unavailable_sensors"]
    assert "sensor.grid_power" in health_info["Test Hub_unavailable_sensors"]


@pytest.fixture
def config_entry() -> MagicMock:
    """Create a mock config entry."""
    entry = MagicMock()
    entry.title = "Test Hub"
    entry.entry_id = "test_entry_id"
    entry.data = {
        "optimizer": "highs",
        "horizon_hours": 24,
        "period_minutes": 5,
        "participants": {},
    }
    return entry


@pytest.fixture
def coordinator(hass: HomeAssistant, config_entry: MagicMock) -> HaeoDataUpdateCoordinator:
    """Create a mock coordinator."""
    coordinator = HaeoDataUpdateCoordinator(hass, config_entry)
    coordinator.check_sensors_available = MagicMock(return_value=(True, []))
    return coordinator
