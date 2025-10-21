"""Test the HAEO coordinator."""

import asyncio
from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from typing import Any
from unittest.mock import Mock, patch

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.haeo.const import (
    ATTR_ENERGY,
    ATTR_POWER,
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON_HOURS,
    CONF_INTEGRATION_TYPE,
    CONF_NAME,
    CONF_PERIOD_MINUTES,
    CONF_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
    OPTIMIZATION_STATUS_FAILED,
    OPTIMIZATION_STATUS_SUCCESS,
)
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.elements import (
    ELEMENT_TYPE_BATTERY,
    ELEMENT_TYPE_CONNECTION,
    ELEMENT_TYPE_GRID,
    collect_element_subentries,
)
from custom_components.haeo.elements.battery import CONF_CAPACITY, CONF_INITIAL_CHARGE_PERCENTAGE
from custom_components.haeo.elements.connection import CONF_MAX_POWER, CONF_SOURCE, CONF_TARGET
from custom_components.haeo.elements.grid import (
    CONF_EXPORT_LIMIT,
    CONF_EXPORT_PRICE,
    CONF_IMPORT_LIMIT,
    CONF_IMPORT_PRICE,
)
from custom_components.haeo.model import Network


@pytest.fixture
def mock_hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a mock hub config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Power Network",
            CONF_HORIZON_HOURS: 1,  # 1 hour for testing
            CONF_PERIOD_MINUTES: 30,  # 30 minutes for testing
            CONF_UPDATE_INTERVAL_MINUTES: 5,
            CONF_DEBOUNCE_SECONDS: 1,
        },
        entry_id="hub_entry_id",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_battery_subentry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> ConfigSubentry:
    """Create a mock battery subentry."""
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_NAME: "test_battery",
                CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
                CONF_CAPACITY: 10000,
                CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_soc",
            }
        ),
        subentry_type=ELEMENT_TYPE_BATTERY,
        title="Test Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_hub_entry, subentry)
    return subentry


@pytest.fixture
def mock_grid_subentry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> ConfigSubentry:
    """Create a mock grid subentry."""
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_NAME: "test_grid",
                CONF_ELEMENT_TYPE: ELEMENT_TYPE_GRID,
                CONF_IMPORT_LIMIT: 10000,
                CONF_EXPORT_LIMIT: 5000,
                CONF_IMPORT_PRICE: {
                    "live": ["sensor.import_price"],
                    "forecast": ["sensor.import_price"],
                },
                CONF_EXPORT_PRICE: {
                    "live": ["sensor.export_price"],
                    "forecast": ["sensor.export_price"],
                },
            }
        ),
        subentry_type=ELEMENT_TYPE_GRID,
        title="Test Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_hub_entry, subentry)
    return subentry


@pytest.fixture
def mock_connection_subentry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> ConfigSubentry:
    """Create a mock connection subentry."""
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_NAME: "test_connection",
                CONF_ELEMENT_TYPE: ELEMENT_TYPE_CONNECTION,
                CONF_SOURCE: "test_battery",
                CONF_TARGET: "test_grid",
                CONF_MAX_POWER: 5000,
            }
        ),
        subentry_type=ELEMENT_TYPE_CONNECTION,
        title="Battery to Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_hub_entry, subentry)
    return subentry


async def test_coordinator_initialization(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Test coordinator initialization."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    assert coordinator.hass == hass
    assert coordinator.entry == mock_hub_entry
    # Participants should be discovered from child subentries
    assert set(coordinator.participant_configs) == {"test_battery", "test_grid"}
    assert coordinator.network is None
    assert coordinator.optimization_result is None
    assert coordinator.update_interval == timedelta(minutes=5)


async def test_update_interval_respects_config(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Ensure coordinator uses configured update interval."""
    hass.config_entries.async_update_entry(
        mock_hub_entry,
        data={**dict(mock_hub_entry.data), CONF_UPDATE_INTERVAL_MINUTES: 12},
    )
    await hass.async_block_till_done()
    assert mock_hub_entry.data[CONF_UPDATE_INTERVAL_MINUTES] == 12
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    assert coordinator.update_interval == timedelta(minutes=12)


@patch("custom_components.haeo.model.network.Network.optimize")
async def test_update_data_success(
    mock_optimize: Mock,
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
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

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

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
    mock_optimize: Mock,
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
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

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Mock optimization failure
    mock_optimize.side_effect = Exception("Optimization failed")

    with patch.object(hass, "async_add_executor_job", side_effect=Exception("Optimization failed")):
        result = await coordinator._async_update_data()

    # Should return dict with None cost for optimization failures during configuration
    assert result is not None
    assert result["cost"] is None
    assert coordinator.optimization_status == OPTIMIZATION_STATUS_FAILED
    assert coordinator.optimization_result is None


def test_get_element_data(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Test getting entity data."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

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


def test_get_element_data_no_result(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Test getting entity data with no optimization result."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    result = coordinator.get_element_data("test_battery")

    assert result is None


def test_last_optimization_properties(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Test last optimization properties."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

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


async def test_get_future_timestamps_no_result(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Test getting future timestamps with no optimization result."""

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    result = coordinator.get_future_timestamps()

    assert result == []


async def test_get_future_timestamps_with_result(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Test getting future timestamps with optimization result."""

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

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


async def test_update_data_network_build_failure(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Test update data when network building fails."""
    # Set up sensor state for battery
    hass.states.async_set("sensor.battery_soc", "50", {"device_class": "battery", "unit_of_measurement": "%"})

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

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


@patch("custom_components.haeo.model.network.Network.optimize")
async def test_calculate_time_parameters_with_integer_values(
    mock_optimize: Mock,
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Test that integer values in config work correctly for horizon_hours and period_minutes."""
    # Config entry with explicit integer values
    int_hub_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            **mock_hub_entry.data,
            CONF_HORIZON_HOURS: 1,  # Integer (as enforced by schema)
            CONF_PERIOD_MINUTES: 30,  # Integer (as enforced by schema)
        },
        entry_id="test_int_entry_id",
    )
    int_hub_entry.add_to_hass(hass)

    # Create new battery and grid subentries with the int_hub as parent
    int_battery_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_NAME: "test_battery",
                CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
                CONF_CAPACITY: 10000,
                CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_soc",
            }
        ),
        subentry_type=ELEMENT_TYPE_BATTERY,
        title="Test Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(int_hub_entry, int_battery_subentry)

    int_grid_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_NAME: "test_grid",
                CONF_ELEMENT_TYPE: ELEMENT_TYPE_GRID,
                CONF_IMPORT_LIMIT: 10000,
                CONF_EXPORT_LIMIT: 5000,
                CONF_IMPORT_PRICE: {
                    "live": ["sensor.import_price"],
                    "forecast": ["sensor.import_price"],
                },
                CONF_EXPORT_PRICE: {
                    "live": ["sensor.export_price"],
                    "forecast": ["sensor.export_price"],
                },
            }
        ),
        subentry_type=ELEMENT_TYPE_GRID,
        title="Test Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(int_hub_entry, int_grid_subentry)

    # Set up sensor states
    hass.states.async_set("sensor.battery_soc", "50", {"device_class": "battery", "unit_of_measurement": "%"})

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

    coordinator = HaeoDataUpdateCoordinator(hass, int_hub_entry)

    # Mock optimization result
    mock_cost = 100.0
    mock_optimize.return_value = mock_cost

    async def async_job() -> float:
        return mock_cost

    # Should work correctly with integer config values
    with patch.object(hass, "async_add_executor_job", return_value=async_job()):
        result = await coordinator._async_update_data()

    # Verify the coordinator successfully handled integer config values
    assert result is not None
    assert coordinator.optimization_status == OPTIMIZATION_STATUS_SUCCESS
    assert coordinator.optimization_result is not None
    assert coordinator.optimization_result["cost"] == mock_cost


@patch("custom_components.haeo.model.network.Network.optimize")
async def test_sensor_state_change_triggers_optimization(
    mock_optimize: Mock,
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Test that sensor state changes trigger optimization refresh."""
    # Set up initial sensor states
    hass.states.async_set("sensor.battery_soc", "50", {"device_class": "battery", "unit_of_measurement": "%"})

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

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Mock optimization result
    mock_cost = 100.0
    mock_optimize.return_value = mock_cost

    # Track how many times refresh is called
    refresh_count = 0
    original_refresh = coordinator.async_refresh

    async def mock_refresh() -> None:
        nonlocal refresh_count
        refresh_count += 1
        await original_refresh()

    with patch.object(coordinator, "async_refresh", mock_refresh):
        # Initial setup
        await hass.async_block_till_done()

        # Change sensor state
        hass.states.async_set("sensor.battery_soc", "60", {"device_class": "battery", "unit_of_measurement": "%"})
        await hass.async_block_till_done()

        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=1))
        await hass.async_block_till_done()

        async def _wait_for_refresh() -> None:
            while refresh_count == 0:
                await hass.async_block_till_done()
                await asyncio.sleep(0)

        await asyncio.wait_for(_wait_for_refresh(), timeout=1)
        assert refresh_count == 1


async def test_debounced_updates_queue_pending_refresh(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Ensure state changes during updates queue a follow-up refresh."""

    hass.states.async_set("sensor.battery_soc", "50", {"device_class": "battery", "unit_of_measurement": "%"})
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

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    call_count = 0
    first_call_started = asyncio.Event()
    continue_event = asyncio.Event()

    async def fake_update() -> dict[str, Any]:
        nonlocal call_count
        coordinator._update_in_progress = True
        call_count += 1
        first_call_started.set()
        await continue_event.wait()
        coordinator._update_in_progress = False
        if coordinator._pending_refresh:
            coordinator._pending_refresh = False
            coordinator._schedule_debounced_refresh(immediate=True)
        return {
            "cost": 1.0,
            "timestamp": dt_util.utcnow(),
            "duration": 0.1,
        }

    def fake_schedule_debounce(*, immediate: bool = False) -> None:
        if immediate:
            coordinator._handle_debounced_refresh(dt_util.utcnow())

    with (
        patch.object(coordinator, "_async_update_data", side_effect=fake_update),
        patch.object(coordinator, "_schedule_debounced_refresh", side_effect=fake_schedule_debounce),
    ):
        refresh_task = hass.async_create_task(coordinator.async_refresh())

        await asyncio.wait_for(first_call_started.wait(), timeout=1)
        assert call_count == 1

        coordinator._handle_debounced_refresh(dt_util.utcnow())
        assert coordinator._pending_refresh

        continue_event.set()

        await refresh_task
        await hass.async_block_till_done()
        await asyncio.sleep(0)

        async def _wait_for_second_call() -> None:
            while call_count < 2:
                await hass.async_block_till_done()
                await asyncio.sleep(0)

        await asyncio.wait_for(_wait_for_second_call(), timeout=1)

        assert call_count == 2


async def test_coordinator_cleanup(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Test that coordinator cleanup properly unsubscribes from state changes."""
    # Set up minimal sensor state
    hass.states.async_set("sensor.battery_soc", "50", {"device_class": "battery", "unit_of_measurement": "%"})

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    # Verify state change listener was set up
    assert coordinator._state_change_unsub is not None

    # Clean up coordinator
    coordinator.cleanup()

    # Verify cleanup occurred
    assert coordinator._state_change_unsub is None


async def test_unavailable_sensors_handling(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
) -> None:
    """Test handling of unavailable sensors during update."""

    # Set battery as available but grid prices as unavailable
    hass.states.async_set("sensor.battery_soc", "50", {"device_class": "battery", "unit_of_measurement": "%"})
    hass.states.async_set("sensor.import_price", "unavailable")
    hass.states.async_set("sensor.export_price", "unknown")

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    result = await coordinator._async_update_data()

    # Should return failed status with None cost when required sensors unavailable
    assert result is not None
    assert result["cost"] is None
    # Sensor unavailability causes optimization failure, not pending state
    assert coordinator.optimization_status == OPTIMIZATION_STATUS_FAILED


async def test_collect_element_subentries_without_participants(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """collect_element_subentries returns empty list when no participants exist."""

    assert collect_element_subentries(mock_hub_entry) == []


async def test_collect_element_subentries_skips_missing_name(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
) -> None:
    """Ensure subentries without a valid name are skipped."""

    bad_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
                CONF_CAPACITY: 1000,
                CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.missing_name_soc",
            }
        ),
        subentry_type=ELEMENT_TYPE_BATTERY,
        title="Bad Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_hub_entry, bad_subentry)

    entries = collect_element_subentries(mock_hub_entry)
    names = {entry.name for entry in entries}

    assert "Bad Battery" not in names
    assert "test_battery" in names
