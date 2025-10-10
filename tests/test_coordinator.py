"""Test the HAEO coordinator."""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

from homeassistant.const import CONF_NAME, CONF_SOURCE, CONF_TARGET
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    ATTR_ENERGY,
    ATTR_POWER,
    CONF_CAPACITY,
    CONF_ELEMENT_TYPE,
    CONF_EXPORT_LIMIT,
    CONF_EXPORT_PRICE,
    CONF_HORIZON_HOURS,
    CONF_IMPORT_LIMIT,
    CONF_IMPORT_PRICE,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_POWER,
    CONF_PARTICIPANTS,
    CONF_PERIOD_MINUTES,
    DOMAIN,
    ELEMENT_TYPE_BATTERY,
    ELEMENT_TYPE_CONNECTION,
    ELEMENT_TYPE_GRID,
    OPTIMIZATION_STATUS_FAILED,
    OPTIMIZATION_STATUS_SUCCESS,
)
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.model import Network


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": "hub",
            CONF_NAME: "Power Network",
            CONF_HORIZON_HOURS: 1,  # 1 hour for testing
            CONF_PERIOD_MINUTES: 30,  # 30 minutes for testing
            CONF_PARTICIPANTS: {
                "test_battery": {
                    CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
                    f"{CONF_CAPACITY}_value": 10000,
                    f"{CONF_INITIAL_CHARGE_PERCENTAGE}_value": "sensor.battery_soc",  # Use sensor for initial charge
                },
                "test_grid": {
                    CONF_ELEMENT_TYPE: ELEMENT_TYPE_GRID,
                    f"{CONF_IMPORT_LIMIT}_value": 10000,
                    f"{CONF_EXPORT_LIMIT}_value": 5000,
                    # Use sensor references instead of constant values
                    f"{CONF_IMPORT_PRICE}_live": ["sensor.import_price"],
                    f"{CONF_IMPORT_PRICE}_forecast": ["sensor.import_price"],
                    f"{CONF_EXPORT_PRICE}_live": ["sensor.export_price"],
                    f"{CONF_EXPORT_PRICE}_forecast": ["sensor.export_price"],
                },
                "test_connection": {
                    CONF_ELEMENT_TYPE: ELEMENT_TYPE_CONNECTION,
                    f"{CONF_SOURCE}_value": "test_battery",
                    f"{CONF_TARGET}_value": "test_grid",
                    f"{CONF_MAX_POWER}_value": 5000,
                },
            },
        },
        entry_id="test_entry_id",
    )


async def test_coordinator_initialization(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test coordinator initialization."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_config_entry)

    assert coordinator.hass == hass
    assert coordinator.entry == mock_config_entry
    assert coordinator.config == mock_config_entry.data
    assert coordinator.network is None
    assert coordinator.optimization_result is None


@patch("custom_components.haeo.model.network.Network.optimize")
async def test_update_data_success(
    mock_optimize: Mock, hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test successful data update."""
    # Set up sensor states for battery and pricing with forecast data in Amber Electric format
    hass.states.async_set("sensor.battery_soc", "50", {"device_class": "battery", "unit_of_measurement": "%"})

    # Create a smaller forecast for testing (2 periods instead of 576)
    forecast_data = [
        {"start_time": "2025-10-05T00:00:00", "per_kwh": 0.1},
        {"start_time": "2025-10-05T00:05:00", "per_kwh": 0.1},
    ]

    hass.states.async_set(
        "sensor.import_price",
        "0.10",
        {"device_class": "monetary", "unit_of_measurement": "$/kWh", "forecasts": forecast_data},
    )
    hass.states.async_set(
        "sensor.export_price",
        "0.05",
        {"device_class": "monetary", "unit_of_measurement": "$/kWh", "forecasts": forecast_data},
    )

    coordinator = HaeoDataUpdateCoordinator(hass, mock_config_entry)

    # Mock optimization result - now returns only cost
    mock_cost = 100.0
    mock_optimize.return_value = mock_cost

    async def async_job() -> float:
        return mock_cost

    with patch.object(hass, "async_add_executor_job", return_value=async_job()):
        result = await coordinator._async_update_data()

    assert result is not None
    assert coordinator.optimization_status == OPTIMIZATION_STATUS_SUCCESS
    assert coordinator.optimization_result is not None
    assert coordinator.optimization_result["cost"] == mock_cost


@patch("custom_components.haeo.model.network.Network.optimize")
async def test_update_data_failure(
    mock_optimize: Mock, hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test failed data update."""
    # Set up sensor states for battery and grid
    hass.states.async_set("sensor.battery_soc", "50", {"device_class": "battery", "unit_of_measurement": "%"})

    # Create a smaller forecast for testing (2 periods instead of 576)
    forecast_data = [
        {"start_time": "2025-10-05T00:00:00", "per_kwh": 0.1},
        {"start_time": "2025-10-05T00:30:00", "per_kwh": 0.1},
    ]

    hass.states.async_set(
        "sensor.import_price",
        "0.10",
        {"device_class": "monetary", "unit_of_measurement": "$/kWh", "forecasts": forecast_data},
    )
    hass.states.async_set(
        "sensor.export_price",
        "0.05",
        {"device_class": "monetary", "unit_of_measurement": "$/kWh", "forecasts": forecast_data},
    )

    coordinator = HaeoDataUpdateCoordinator(hass, mock_config_entry)

    # Mock optimization failure
    mock_optimize.side_effect = Exception("Optimization failed")

    with patch.object(hass, "async_add_executor_job", side_effect=Exception("Optimization failed")):
        result = await coordinator._async_update_data()

    # Should return dict with None cost for optimization failures during configuration
    assert result is not None
    assert result["cost"] is None
    assert coordinator.optimization_status == OPTIMIZATION_STATUS_FAILED
    assert coordinator.optimization_result is None


def test_get_element_data(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test getting entity data."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_config_entry)

    # Build a network with entities
    coordinator.network = Network("test", period=3600, n_periods=3)
    coordinator.network.add(
        ELEMENT_TYPE_BATTERY,
        "test_battery",
        capacity=1000,
        initial_charge_percentage=50,
        max_charge_power=100,
        max_discharge_power=100,
    )

    # Run a simple optimization to set variable values
    coordinator.network.optimize()

    result = coordinator.get_element_data("test_battery")

    assert result is not None
    assert ATTR_POWER in result
    assert ATTR_ENERGY in result
    assert len(result[ATTR_POWER]) == 3
    assert len(result[ATTR_ENERGY]) == 3


def test_get_element_data_no_result(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test getting entity data with no optimization result."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_config_entry)

    result = coordinator.get_element_data("test_battery")

    assert result is None


def test_last_optimization_properties(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test last optimization properties."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_config_entry)

    # Initially no optimization result
    assert coordinator.last_optimization_cost is None
    assert coordinator.last_optimization_time is None

    # Set optimization result
    test_time = datetime.now(UTC)
    coordinator.optimization_result = {
        "cost": 150.0,
        "solution": {},
        "timestamp": test_time,
    }

    assert coordinator.last_optimization_cost == 150.0
    assert coordinator.last_optimization_time == test_time


async def test_get_future_timestamps_no_result(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test getting future timestamps with no optimization result."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_config_entry)

    result = coordinator.get_future_timestamps()

    assert result == []


async def test_get_future_timestamps_with_result(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test getting future timestamps with optimization result."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_config_entry)

    # Create a network for the coordinator
    coordinator.network = Network("test", period=1800, n_periods=2)

    # Set optimization result with timestamp
    test_time = datetime.now(UTC)
    coordinator.optimization_result = {
        "cost": 150.0,
        "timestamp": test_time,
    }

    result = coordinator.get_future_timestamps()

    assert len(result) == 2  # 2 periods (1 hour in 30-minute steps)
    # Check that timestamps are ISO format strings
    for timestamp in result:
        assert isinstance(timestamp, str)
        # Should be able to parse as datetime
        datetime.fromisoformat(timestamp)


async def test_update_data_network_build_failure(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test update data when network building fails."""
    # Set up sensor state for battery
    hass.states.async_set("sensor.battery_soc", "50", {"device_class": "battery", "unit_of_measurement": "%"})

    coordinator = HaeoDataUpdateCoordinator(hass, mock_config_entry)

    # Mock failing network build (which now includes sensor data loading)
    with (
        patch("custom_components.haeo.data.load_network", side_effect=ValueError("Network build failed")),
        patch("custom_components.haeo.model.network.Network.optimize", return_value=100.0),
    ):
        result = await coordinator._async_update_data()

    # Should return a result even when network building fails
    assert result is not None
    assert result["cost"] is None
    assert coordinator.optimization_status == OPTIMIZATION_STATUS_FAILED
