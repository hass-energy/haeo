"""Test the HAEO sensor platform."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

from homeassistant.const import CURRENCY_DOLLAR
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    ATTR_ENERGY,
    ATTR_POWER,
    CONF_ELEMENT_TYPE,
    DOMAIN,
    ELEMENT_TYPE_BATTERY,
    ELEMENT_TYPE_CONNECTION,
    ELEMENT_TYPE_CONSTANT_LOAD,
    ELEMENT_TYPE_FORECAST_LOAD,
    ELEMENT_TYPE_GRID,
    ELEMENT_TYPE_NET,
    ELEMENT_TYPE_NETWORK,
    ELEMENT_TYPE_PHOTOVOLTAICS,
    OPTIMIZATION_STATUS_FAILED,
    OPTIMIZATION_STATUS_SUCCESS,
)
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.sensors import async_setup_entry
from custom_components.haeo.sensors.base import HaeoSensorBase
from custom_components.haeo.sensors.cost import HaeoCostSensor
from custom_components.haeo.sensors.energy import HaeoEnergySensor
from custom_components.haeo.sensors.optimization import HaeoOptimizationCostSensor, HaeoOptimizationStatusSensor
from custom_components.haeo.sensors.power import HaeoPowerSensor
from custom_components.haeo.sensors.soc import HaeoSOCSensor


@pytest.fixture
def mock_coordinator() -> HaeoDataUpdateCoordinator:
    """Create a mock coordinator."""
    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.last_update_success = True
    coordinator.optimization_status = OPTIMIZATION_STATUS_SUCCESS
    coordinator.last_optimization_cost = 15.50
    coordinator.last_optimization_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    coordinator.optimization_result = {
        "solution": {
            "test_battery_power": [50.0, 75.0, 100.0],  # Battery transporting power
            "test_battery_energy": [500.0, 600.0, 700.0],
        },
    }
    coordinator.get_element_data.return_value = {
        ATTR_POWER: [-50.0, -75.0, -100.0],  # Net power (negative = consuming)
        ATTR_ENERGY: [500.0, 600.0, 700.0],
    }
    coordinator.get_future_timestamps.return_value = [
        datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 14, 0, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 15, 0, 0, tzinfo=UTC),
    ]
    return coordinator


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        title="Test HAEO",
        domain=DOMAIN,
        entry_id="test_entry",
        data={
            "participants": {
                "test_battery": {CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY},
                "test_grid": {CONF_ELEMENT_TYPE: ELEMENT_TYPE_GRID},
                "test_load_fixed": {CONF_ELEMENT_TYPE: ELEMENT_TYPE_CONSTANT_LOAD},
                "test_load_forecast": {CONF_ELEMENT_TYPE: ELEMENT_TYPE_FORECAST_LOAD},
                "test_connection": {CONF_ELEMENT_TYPE: ELEMENT_TYPE_CONNECTION},
            },
        },
    )


@pytest.fixture
def mock_add_entities() -> AsyncMock:
    """Create a mock add entities callback."""
    return AsyncMock()


async def test_async_setup_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_coordinator: HaeoDataUpdateCoordinator,
    mock_add_entities: AsyncMock,
) -> None:
    """Test setting up sensors from config entry."""
    mock_config_entry.add_to_hass(hass)
    mock_config_entry.runtime_data = mock_coordinator

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Verify that entities were added
    mock_add_entities.assert_called_once()
    added_entities = mock_add_entities.call_args[0][0]

    # Should have optimization sensors + entity sensors + connection sensors
    assert len(added_entities) >= 2  # At least cost and status sensors

    # Check for specific sensor types
    sensor_types = [type(entity).__name__ for entity in added_entities]
    assert "HaeoOptimizationCostSensor" in sensor_types
    assert "HaeoOptimizationStatusSensor" in sensor_types


async def test_async_setup_entry_no_coordinator(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_add_entities: AsyncMock
) -> None:
    """Test setting up sensors with no coordinator."""
    mock_config_entry.add_to_hass(hass)
    # Don't set runtime_data (coordinator)
    # MockConfigEntry doesn't have runtime_data attribute by default

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Should not add any entities when no coordinator
    mock_add_entities.assert_not_called()


def test_sensor_base_init(mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry) -> None:
    """Test sensor base initialization."""
    sensor = HaeoSensorBase(
        mock_coordinator, mock_config_entry, "test_type", "Test Sensor", "test_element", "test_element_type"
    )

    assert sensor.config_entry == mock_config_entry
    assert sensor.sensor_type == "test_type"
    assert sensor.element_name == "test_element"
    assert sensor.element_type == "test_element_type"
    assert sensor._attr_name == "HAEO test_element Test Sensor"
    assert sensor._attr_unique_id == f"{mock_config_entry.entry_id}_test_type"


def test_sensor_base_device_info(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test device info property for network-level sensor."""
    sensor = HaeoSensorBase(
        mock_coordinator, mock_config_entry, "test_type", "Test Sensor", "network", ELEMENT_TYPE_NETWORK
    )
    device_info = sensor.device_info

    assert device_info is not None
    assert device_info.get("identifiers") == {(DOMAIN, mock_config_entry.entry_id)}
    assert device_info.get("name") == "HAEO Network"
    assert device_info.get("manufacturer") == "HAEO"
    assert device_info.get("model") == "network"


def test_sensor_base_available_success(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test availability when coordinator is successful."""
    mock_coordinator.last_update_success = True
    sensor = HaeoSensorBase(mock_coordinator, mock_config_entry, "test_type", "Test Sensor", "network", "network")

    assert sensor.available is True


def test_sensor_base_available_failure(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test availability when coordinator fails."""
    mock_coordinator.last_update_success = False
    sensor = HaeoSensorBase(mock_coordinator, mock_config_entry, "test_type", "Test Sensor", "network", "network")

    assert sensor.available is False


def test_sensor_base_device_info_with_element(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test device info property with element info."""
    sensor = HaeoSensorBase(
        mock_coordinator,
        mock_config_entry,
        "test_type",
        "Test Sensor",
        "test_battery",
        ELEMENT_TYPE_BATTERY,
    )
    device_info = sensor.device_info

    assert device_info is not None
    assert device_info.get("identifiers") == {(DOMAIN, f"{mock_config_entry.entry_id}_test_battery")}
    assert device_info.get("name") == "test_battery"
    assert device_info.get("manufacturer") == "HAEO"
    assert device_info.get("model") == "battery"


def test_optimization_cost_sensor_init(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test sensor initialization."""
    sensor = HaeoOptimizationCostSensor(mock_coordinator, mock_config_entry)

    assert sensor._attr_name == "HAEO network Optimization Cost"
    assert sensor._attr_native_unit_of_measurement == CURRENCY_DOLLAR
    assert sensor._attr_unique_id == f"{mock_config_entry.entry_id}_network_cost"


def test_optimization_cost_sensor_native_value(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test native value property."""
    sensor = HaeoOptimizationCostSensor(mock_coordinator, mock_config_entry)
    assert sensor.native_value == 15.50


def test_optimization_cost_sensor_native_value_none(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test native value when no cost available."""
    mock_coordinator.last_optimization_cost = None
    sensor = HaeoOptimizationCostSensor(mock_coordinator, mock_config_entry)
    assert sensor.native_value is None


def test_optimization_cost_sensor_extra_state_attributes(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test extra state attributes."""
    sensor = HaeoOptimizationCostSensor(mock_coordinator, mock_config_entry)
    attrs = sensor.extra_state_attributes

    assert attrs is not None
    assert "last_optimization" in attrs
    assert attrs["last_optimization"] == "2024-01-01T12:00:00+00:00"
    assert attrs["optimization_status"] == OPTIMIZATION_STATUS_SUCCESS


def test_optimization_cost_sensor_extra_state_attributes_no_time(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test extra state attributes when no optimization time."""
    mock_coordinator.last_optimization_time = None
    sensor = HaeoOptimizationCostSensor(mock_coordinator, mock_config_entry)
    attrs = sensor.extra_state_attributes

    assert attrs is not None
    assert "last_optimization" not in attrs
    assert attrs["optimization_status"] == OPTIMIZATION_STATUS_SUCCESS


def test_optimization_status_sensor_init(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test sensor initialization."""
    sensor = HaeoOptimizationStatusSensor(mock_coordinator, mock_config_entry)

    assert sensor._attr_name == "HAEO network Optimization Status"
    assert sensor._attr_unique_id == f"{mock_config_entry.entry_id}_optimization_status"


def test_optimization_status_sensor_native_value_success(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test native value for successful optimization."""
    sensor = HaeoOptimizationStatusSensor(mock_coordinator, mock_config_entry)
    assert sensor.native_value == OPTIMIZATION_STATUS_SUCCESS


def test_optimization_status_sensor_native_value_failure(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test native value for failed optimization."""
    mock_coordinator.optimization_status = OPTIMIZATION_STATUS_FAILED
    sensor = HaeoOptimizationStatusSensor(mock_coordinator, mock_config_entry)
    assert sensor.native_value == OPTIMIZATION_STATUS_FAILED


def test_optimization_status_sensor_icon_success(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test icon for successful optimization."""
    sensor = HaeoOptimizationStatusSensor(mock_coordinator, mock_config_entry)
    assert sensor.icon == "mdi:check-circle"


def test_optimization_status_sensor_icon_failure(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test icon for failed optimization."""
    mock_coordinator.optimization_status = OPTIMIZATION_STATUS_FAILED
    sensor = HaeoOptimizationStatusSensor(mock_coordinator, mock_config_entry)
    assert sensor.icon == "mdi:alert-circle"


def test_optimization_status_sensor_extra_state_attributes(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test extra state attributes."""
    sensor = HaeoOptimizationStatusSensor(mock_coordinator, mock_config_entry)
    attrs = sensor.extra_state_attributes

    assert attrs is not None
    assert attrs["last_optimization"] == "2024-01-01T12:00:00+00:00"
    assert attrs["last_cost"] == 15.50


@pytest.mark.parametrize(
    ("sensor_class", "expected_name_suffix", "expected_unique_id"),
    [
        (HaeoPowerSensor, "Power", "power"),
        (HaeoEnergySensor, "Energy", "energy"),
        (HaeoSOCSensor, "State of Charge", "state_of_charge"),
        (HaeoCostSensor, "Cost", "cost"),
    ],
)
def test_element_sensor_init(
    mock_coordinator: HaeoDataUpdateCoordinator,
    mock_config_entry: MockConfigEntry,
    sensor_class: type,
    expected_name_suffix: str,
    expected_unique_id: str,
) -> None:
    """Test element sensor initialization."""
    sensor = sensor_class(mock_coordinator, mock_config_entry, "test_battery", ELEMENT_TYPE_BATTERY)

    assert sensor.element_name == "test_battery"
    assert sensor._attr_name == f"HAEO test_battery {expected_name_suffix}"
    assert sensor._attr_unique_id == f"{mock_config_entry.entry_id}_test_battery_{expected_unique_id}"


@pytest.mark.parametrize(
    "sensor_class",
    [HaeoPowerSensor, HaeoEnergySensor, HaeoSOCSensor, HaeoCostSensor],
)
def test_element_sensor_native_value(
    mock_coordinator: HaeoDataUpdateCoordinator,
    mock_config_entry: MockConfigEntry,
    sensor_class: type,
) -> None:
    """Test element sensor native value property."""
    # SOC sensor needs additional setup for mock element
    if sensor_class == HaeoSOCSensor:
        mock_element = Mock()
        mock_element.capacity = 10000
        mock_network = Mock()
        mock_network.elements = {"test_battery": mock_element}
        mock_coordinator.network = mock_network

    sensor = sensor_class(mock_coordinator, mock_config_entry, "test_battery", ELEMENT_TYPE_BATTERY)
    # Cost sensor returns None for element-level (not implemented yet), others return numeric
    if sensor_class == HaeoCostSensor:
        assert sensor.native_value is None
    else:
        assert sensor.native_value is not None
        assert isinstance(sensor.native_value, (int, float))


@pytest.mark.parametrize(
    "sensor_class",
    [HaeoPowerSensor, HaeoEnergySensor, HaeoSOCSensor, HaeoCostSensor],
)
def test_element_sensor_native_value_no_data(
    mock_coordinator: HaeoDataUpdateCoordinator,
    mock_config_entry: MockConfigEntry,
    sensor_class: type,
) -> None:
    """Test element sensor native value when no data available."""
    mock_coordinator.get_element_data.return_value = None
    sensor = sensor_class(mock_coordinator, mock_config_entry, "test_battery", ELEMENT_TYPE_BATTERY)
    assert sensor.native_value is None


@pytest.mark.parametrize(
    ("sensor_class", "attribute_key"),
    [
        (HaeoPowerSensor, ATTR_POWER),
        (HaeoEnergySensor, ATTR_ENERGY),
        (HaeoSOCSensor, ATTR_ENERGY),
    ],
)
def test_element_sensor_native_value_empty_data(
    mock_coordinator: HaeoDataUpdateCoordinator,
    mock_config_entry: MockConfigEntry,
    sensor_class: type,
    attribute_key: str,
) -> None:
    """Test element sensor native value when data is empty."""
    mock_coordinator.get_element_data.return_value = {attribute_key: []}
    sensor = sensor_class(mock_coordinator, mock_config_entry, "test_battery", ELEMENT_TYPE_BATTERY)
    assert sensor.native_value is None


@pytest.mark.parametrize(
    "sensor_class",
    [HaeoPowerSensor, HaeoEnergySensor, HaeoSOCSensor],
)
def test_element_sensor_extra_state_attributes(
    mock_coordinator: HaeoDataUpdateCoordinator,
    mock_config_entry: MockConfigEntry,
    sensor_class: type,
) -> None:
    """Test element sensor extra state attributes."""
    # SOC sensor needs additional setup for mock element
    if sensor_class == HaeoSOCSensor:
        mock_element = Mock()
        mock_element.capacity = 10000
        mock_network = Mock()
        mock_network.elements = {"test_battery": mock_element}
        mock_coordinator.network = mock_network

    sensor = sensor_class(mock_coordinator, mock_config_entry, "test_battery", ELEMENT_TYPE_BATTERY)
    attrs = sensor.extra_state_attributes

    assert attrs is not None
    assert "forecast" in attrs
    assert isinstance(attrs["forecast"], list)
    assert len(attrs["forecast"]) == 3
    assert "timestamped_forecast" in attrs
    assert len(attrs["timestamped_forecast"]) == 3
    assert "value" in attrs["timestamped_forecast"][0]


@pytest.mark.parametrize(
    ("element_name", "element_type", "expected_model"),
    [
        ("test_battery", ELEMENT_TYPE_BATTERY, "battery"),
        ("test_grid", ELEMENT_TYPE_GRID, "grid"),
        ("test_photovoltaics", ELEMENT_TYPE_PHOTOVOLTAICS, "photovoltaics"),
        ("test_load_constant", ELEMENT_TYPE_CONSTANT_LOAD, "constant_load"),
        ("test_load_forecast", ELEMENT_TYPE_FORECAST_LOAD, "forecast_load"),
        ("test_net", ELEMENT_TYPE_NET, "net"),
        ("test_connection", ELEMENT_TYPE_CONNECTION, "connection"),
    ],
)
def test_sensor_base_device_info_with_element_types(
    mock_coordinator: HaeoDataUpdateCoordinator,
    mock_config_entry: MockConfigEntry,
    element_name: str,
    element_type: str,
    expected_model: str,
) -> None:
    """Test device info property with different element types."""
    sensor = HaeoSensorBase(
        mock_coordinator,
        mock_config_entry,
        "test_type",
        "Test Sensor",
        element_name,
        element_type,
    )
    device_info = sensor.device_info

    assert device_info is not None
    assert device_info.get("identifiers") == {(DOMAIN, f"{mock_config_entry.entry_id}_{element_name}")}
    assert device_info.get("name") == element_name
    assert device_info.get("manufacturer") == "HAEO"
    assert device_info.get("model") == expected_model


def test_coordinator_get_element_data_exception(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test handling exception when getting element data."""
    # Set up normal data first
    mock_coordinator.get_element_data.return_value = {
        ATTR_POWER: [-50.0, -75.0, -100.0],
    }

    sensor = HaeoPowerSensor(mock_coordinator, mock_config_entry, "test_battery", ELEMENT_TYPE_BATTERY)

    # First verify normal operation
    assert sensor.native_value == -50.0

    # Now make get_element_data raise an exception
    mock_coordinator.get_element_data.side_effect = Exception("Data retrieval failed")

    # Create a new sensor instance to test error handling
    sensor_error = HaeoPowerSensor(mock_coordinator, mock_config_entry, "test_battery", ELEMENT_TYPE_BATTERY)

    # Should handle gracefully and return None
    assert sensor_error.native_value is None


def test_coordinator_get_future_timestamps_exception(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test handling exception when getting future timestamps."""
    # Set up normal data - keep get_element_data working but make get_future_timestamps fail
    mock_coordinator.get_element_data.return_value = {
        ATTR_POWER: [-50.0, -75.0, -100.0],
    }

    sensor = HaeoPowerSensor(mock_coordinator, mock_config_entry, "test_battery", ELEMENT_TYPE_BATTERY)

    # First verify normal operation
    attrs = sensor.extra_state_attributes
    assert attrs is not None
    assert "forecast" in attrs
    assert "timestamped_forecast" in attrs

    # Now make get_future_timestamps raise an exception
    mock_coordinator.get_future_timestamps.side_effect = Exception("Timestamp retrieval failed")

    # Create a new sensor instance to test error handling
    sensor_error = HaeoPowerSensor(mock_coordinator, mock_config_entry, "test_battery", ELEMENT_TYPE_BATTERY)

    # Should handle gracefully - the method should not raise an exception
    # and should return attributes with forecast but without timestamped_forecast
    attrs_error = sensor_error.extra_state_attributes
    assert attrs_error is not None
    assert "forecast" in attrs_error
    # timestamped_forecast should be missing due to the exception
    assert "timestamped_forecast" not in attrs_error


def test_sensor_available_with_coordinator_exception(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test sensor availability when coordinator throws exceptions."""
    # Make get_element_data raise an exception
    mock_coordinator.get_element_data.side_effect = Exception("Coordinator error")

    sensor = HaeoPowerSensor(mock_coordinator, mock_config_entry, "test_battery", ELEMENT_TYPE_BATTERY)

    # Sensor should be unavailable when coordinator fails
    assert sensor.available is False


def test_sensor_available_with_no_element_data(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test sensor availability when element data is None."""
    # Return None for element data (no data available)
    mock_coordinator.get_element_data.return_value = None

    sensor = HaeoPowerSensor(mock_coordinator, mock_config_entry, "test_battery", ELEMENT_TYPE_BATTERY)

    # Sensor should be unavailable when no data is available
    assert sensor.available is False


def test_optimization_sensor_available_pending_status(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test optimization sensor availability with pending status."""
    # Set up coordinator with pending status and no results
    mock_coordinator.optimization_result = None
    mock_coordinator.optimization_status = "pending"

    sensor = HaeoOptimizationCostSensor(mock_coordinator, mock_config_entry)

    # Sensor should be unavailable when status is pending and no results
    assert sensor.available is False


def test_optimization_sensor_available_with_results(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test optimization sensor availability with results."""
    # Set up coordinator with results
    mock_coordinator.optimization_result = {"cost": 100.0}
    mock_coordinator.optimization_status = "success"

    sensor = HaeoOptimizationCostSensor(mock_coordinator, mock_config_entry)

    # Sensor should be available when results exist
    assert sensor.available is True


def test_native_value_with_no_element_data(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test native value when element data is missing."""
    # Return None for element data
    mock_coordinator.get_element_data.return_value = None

    sensor = HaeoPowerSensor(mock_coordinator, mock_config_entry, "test_battery", ELEMENT_TYPE_BATTERY)

    # Should return None gracefully
    assert sensor.native_value is None


def test_native_value_with_empty_element_data(
    mock_coordinator: HaeoDataUpdateCoordinator, mock_config_entry: MockConfigEntry
) -> None:
    """Test native value when element data is empty."""
    # Return empty dict for element data
    mock_coordinator.get_element_data.return_value = {}

    sensor = HaeoPowerSensor(mock_coordinator, mock_config_entry, "test_battery", ELEMENT_TYPE_BATTERY)

    # Should return None gracefully
    assert sensor.native_value is None


def test_sensor_unavailable_when_sensor_data_missing(mock_config_entry: MockConfigEntry) -> None:
    """Test that sensors show as unavailable when underlying sensor data is missing."""
    # Create a coordinator with missing sensor data
    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.last_update_success = True  # Required for coordinator availability
    coordinator.optimization_status = OPTIMIZATION_STATUS_FAILED
    coordinator.optimization_result = None
    coordinator.get_element_data = Mock(return_value=None)  # Simulate missing element data

    # Create a power sensor
    sensor = HaeoPowerSensor(coordinator, mock_config_entry, "test_battery", ELEMENT_TYPE_BATTERY)

    # The sensor should be unavailable when element data is missing
    assert not sensor.available

    # Test optimization status sensor
    status_sensor = HaeoOptimizationStatusSensor(coordinator, mock_config_entry)

    # Should be available since optimization status is set (even if failed)
    assert status_sensor.available
    assert status_sensor.native_value == OPTIMIZATION_STATUS_FAILED


@pytest.mark.parametrize(
    "sensor_class",
    [HaeoPowerSensor, HaeoEnergySensor, HaeoSOCSensor],
)
def test_sensor_native_value_with_exception(
    mock_coordinator: HaeoDataUpdateCoordinator,
    mock_config_entry: MockConfigEntry,
    sensor_class: type,
) -> None:
    """Test that sensors return None when exception occurs accessing data."""
    mock_coordinator.get_element_data.side_effect = RuntimeError("Data access error")

    sensor = sensor_class(mock_coordinator, mock_config_entry, "test_battery", ELEMENT_TYPE_BATTERY)

    assert sensor.native_value is None


@pytest.mark.parametrize(
    ("sensor_class", "attribute_key"),
    [
        (HaeoPowerSensor, ATTR_POWER),
        (HaeoEnergySensor, ATTR_ENERGY),
        (HaeoSOCSensor, ATTR_ENERGY),
    ],
)
def test_sensor_extra_attributes_with_exception(
    mock_coordinator: HaeoDataUpdateCoordinator,
    mock_config_entry: MockConfigEntry,
    sensor_class: type,
    attribute_key: str,
) -> None:
    """Test that sensors handle timestamp exceptions gracefully in extra_state_attributes."""
    # SOC sensor needs additional setup for mock element
    if sensor_class == HaeoSOCSensor:
        mock_element = Mock()
        mock_element.capacity = 10000
        mock_network = Mock()
        mock_network.elements = {"test_battery": mock_element}
        mock_coordinator.network = mock_network

    mock_coordinator.get_element_data.return_value = {attribute_key: [100.0, 200.0, 300.0]}
    mock_coordinator.get_future_timestamps.side_effect = RuntimeError("Timestamp error")

    sensor = sensor_class(mock_coordinator, mock_config_entry, "test_battery", ELEMENT_TYPE_BATTERY)

    attrs = sensor.extra_state_attributes
    assert attrs is not None
    assert "forecast" in attrs
    assert "timestamped_forecast" not in attrs
