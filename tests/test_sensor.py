"""Test the HAEO sensor platform."""

from collections.abc import Callable
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    ATTR_ENERGY,
    ATTR_POWER,
    CONF_ELEMENT_TYPE,
    CONF_PARTICIPANTS,
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
    OPTIMIZATION_STATUS_FAILED,
    OPTIMIZATION_STATUS_PENDING,
    OPTIMIZATION_STATUS_SUCCESS,
)
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.elements import (
    ELEMENT_TYPE_BATTERY,
    ELEMENT_TYPE_CONNECTION,
    ELEMENT_TYPE_CONSTANT_LOAD,
    ELEMENT_TYPE_FORECAST_LOAD,
    ELEMENT_TYPE_GRID,
    ELEMENT_TYPE_NODE,
    ELEMENT_TYPE_PHOTOVOLTAICS,
    ELEMENT_TYPES,
)
from custom_components.haeo.sensors import SENSOR_TYPES, async_setup_entry
from custom_components.haeo.sensors.base import HaeoSensorBase
from custom_components.haeo.sensors.optimization import (
    HaeoOptimizationCostSensor,
    HaeoOptimizationDurationSensor,
    HaeoOptimizationStatusSensor,
)
from custom_components.haeo.sensors.power import HaeoPowerSensor
from tests.conftest import SensorTestData

type SubentryFactory = Callable[[str, str], ConfigSubentry]

ELEMENT_SENSOR_KEYS = ["power", "energy", "soc", "element_cost"]
FORECAST_SENSOR_KEYS = ["power", "energy", "soc"]
OPTIMIZATION_SENSOR_KEYS = ["optimization_cost", "optimization_status", "optimization_duration"]


def _ensure_capacity(metadata: SensorTestData, coordinator: Any) -> None:
    """Ensure coordinator has capacity information when required."""

    if metadata.requires_capacity:
        element = Mock()
        element.capacity = 10_000
        network = Mock()
        network.elements = {metadata.element_name: element}
        coordinator.network = network


def instantiate_sensor(
    metadata: SensorTestData,
    coordinator: Any,
    factory: SubentryFactory,
    device_id: str,
) -> tuple[HaeoSensorBase, ConfigSubentry]:
    """Create a sensor instance from structured metadata."""

    subentry = factory(metadata.element_name, metadata.element_type)
    if metadata.category == "optimization":
        sensor = metadata.cls(coordinator, subentry, device_id)
    else:
        sensor = metadata.cls(
            coordinator,
            subentry,
            metadata.element_name,
            metadata.element_type,
            device_id,
        )
    return cast("HaeoSensorBase", sensor), subentry


@pytest.fixture
def mock_coordinator(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> Mock:
    """Create a mock coordinator."""

    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.hass = hass
    coordinator.config_entry = mock_config_entry
    coordinator.last_update_success = True
    coordinator.optimization_status = OPTIMIZATION_STATUS_SUCCESS
    coordinator.last_optimization_cost = 15.50
    coordinator.last_optimization_duration = 7.5
    coordinator.last_optimization_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    coordinator.optimization_result = {
        "solution": {
            "test_battery_power": [50.0, 75.0, 100.0],
            "test_battery_energy": [500.0, 600.0, 700.0],
        },
    }
    coordinator.get_element_data.return_value = {
        ATTR_POWER: [-50.0, -75.0, -100.0],
        ATTR_ENERGY: [500.0, 600.0, 700.0],
    }
    coordinator.get_future_timestamps.return_value = [
        datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 14, 0, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 15, 0, 0, tzinfo=UTC),
    ]
    coordinator.config = {
        CONF_PARTICIPANTS: {
            "test_battery": {CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY},
            "test_grid": {CONF_ELEMENT_TYPE: ELEMENT_TYPE_GRID},
            "test_load_fixed": {CONF_ELEMENT_TYPE: ELEMENT_TYPE_CONSTANT_LOAD},
            "test_load_forecast": {CONF_ELEMENT_TYPE: ELEMENT_TYPE_FORECAST_LOAD},
            "test_connection": {CONF_ELEMENT_TYPE: ELEMENT_TYPE_CONNECTION},
        },
    }
    coordinator.network = None
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


@pytest.fixture
def mock_device_id() -> str:
    """Return a mock device ID."""

    return "test_device_id"


@pytest.fixture
def subentry_factory(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> SubentryFactory:
    """Return a factory for creating config subentries in tests."""

    entry_added = False

    def factory(element_name: str, element_type: str) -> ConfigSubentry:
        nonlocal entry_added
        if not entry_added:
            mock_config_entry.add_to_hass(hass)
            entry_added = True
        subentry = ConfigSubentry(
            data=MappingProxyType({"name_value": element_name}),
            subentry_type=element_type,
            title=element_name.replace("_", " ").title(),
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(mock_config_entry, subentry)
        return subentry

    return factory


async def test_async_setup_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_coordinator: Mock,
    mock_add_entities: AsyncMock,
    subentry_factory: SubentryFactory,
) -> None:
    """Test setting up sensors from a config entry."""

    mock_config_entry.runtime_data = mock_coordinator

    subentry_factory("network", ELEMENT_TYPE_NETWORK)
    for name, participant in mock_coordinator.config[CONF_PARTICIPANTS].items():
        subentry_factory(name, participant[CONF_ELEMENT_TYPE])

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    mock_add_entities.assert_called_once()
    added_entities = mock_add_entities.call_args[0][0]
    sensor_types = {type(entity) for entity in added_entities}

    assert HaeoOptimizationCostSensor in sensor_types
    assert HaeoOptimizationStatusSensor in sensor_types
    assert HaeoOptimizationDurationSensor in sensor_types
    assert any(isinstance(entity, HaeoPowerSensor) for entity in added_entities)


async def test_async_setup_entry_no_coordinator(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_add_entities: AsyncMock,
    subentry_factory: SubentryFactory,
) -> None:
    """Test that sensors are not created when coordinator is missing."""

    subentry_factory("network", ELEMENT_TYPE_NETWORK)

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    mock_add_entities.assert_not_called()


def test_sensor_base_init(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
) -> None:
    """Test sensor base initialization."""

    subentry = subentry_factory("test_element", "test_element_type")
    sensor = HaeoSensorBase(
        mock_coordinator,
        subentry,
        "test_type",
        "Test Sensor",
        "test_element",
        "test_element_type",
        mock_device_id,
    )

    assert sensor.sensor_type == "test_type"
    assert sensor.element_name == "test_element"
    assert sensor.element_type == "test_element_type"
    assert sensor._attr_name == "HAEO test_element Test Sensor"
    assert sensor._attr_unique_id == f"{subentry.subentry_id}_test_type"


def test_sensor_base_device_info(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
) -> None:
    """Test device entry linking for a network sensor."""

    subentry = subentry_factory("network", ELEMENT_TYPE_NETWORK)
    sensor = HaeoSensorBase(
        mock_coordinator,
        subentry,
        "test_type",
        "Test Sensor",
        "network",
        ELEMENT_TYPE_NETWORK,
        mock_device_id,
    )

    assert sensor.device_id is None
    assert sensor.device_entry is None


def test_sensor_base_available_success(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
) -> None:
    """Test availability when coordinator is successful."""

    subentry = subentry_factory("network", ELEMENT_TYPE_NETWORK)
    sensor = HaeoSensorBase(
        mock_coordinator,
        subentry,
        "test_type",
        "Test Sensor",
        "network",
        ELEMENT_TYPE_NETWORK,
        mock_device_id,
    )

    assert sensor.available is True


def test_sensor_base_available_failure(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
) -> None:
    """Test availability when coordinator fails."""

    mock_coordinator.last_update_success = False
    subentry = subentry_factory("network", ELEMENT_TYPE_NETWORK)
    sensor = HaeoSensorBase(
        mock_coordinator,
        subentry,
        "test_type",
        "Test Sensor",
        "network",
        ELEMENT_TYPE_NETWORK,
        mock_device_id,
    )

    assert sensor.available is False


@pytest.mark.parametrize(
    ("element_name", "element_type"),
    [
        ("test_battery", ELEMENT_TYPE_BATTERY),
        ("test_grid", ELEMENT_TYPE_GRID),
        ("test_photovoltaics", ELEMENT_TYPE_PHOTOVOLTAICS),
        ("test_load_constant", ELEMENT_TYPE_CONSTANT_LOAD),
        ("test_load_forecast", ELEMENT_TYPE_FORECAST_LOAD),
        ("test_node", ELEMENT_TYPE_NODE),
        ("test_connection", ELEMENT_TYPE_CONNECTION),
    ],
)
def test_sensor_base_device_info_with_element_types(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    element_name: str,
    element_type: str,
) -> None:
    """Test device entry linking for different element types."""

    subentry = subentry_factory(element_name, element_type)
    sensor = HaeoSensorBase(
        mock_coordinator,
        subentry,
        "test_type",
        "Test Sensor",
        element_name,
        element_type,
        mock_device_id,
    )

    assert sensor.device_id is None
    assert sensor.device_entry is None


@pytest.mark.parametrize("sensor_key", ELEMENT_SENSOR_KEYS)
def test_element_sensor_init(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
    sensor_key: str,
) -> None:
    """Test element sensor initialization."""

    metadata = sensor_test_data[sensor_key]
    _ensure_capacity(metadata, mock_coordinator)
    sensor, subentry = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert sensor.element_name == metadata.element_name
    assert sensor._attr_name == f"HAEO {metadata.element_name} {metadata.name_suffix}"
    assert sensor._attr_unique_id == f"{subentry.subentry_id}_{metadata.unique_suffix}"
    assert sensor._attr_translation_key == metadata.translation_key


@pytest.mark.parametrize("sensor_key", ELEMENT_SENSOR_KEYS)
def test_element_sensor_native_value(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
    sensor_key: str,
) -> None:
    """Test element sensor native value property."""

    metadata = sensor_test_data[sensor_key]
    _ensure_capacity(metadata, mock_coordinator)
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    value = sensor.native_value
    if metadata.expect_native_value:
        assert value is not None
        assert isinstance(value, (int, float))
    else:
        assert value is None


@pytest.mark.parametrize("sensor_key", ELEMENT_SENSOR_KEYS)
def test_element_sensor_native_value_no_data(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
    sensor_key: str,
) -> None:
    """Test element sensor native value when coordinator returns no data."""

    metadata = sensor_test_data[sensor_key]
    mock_coordinator.get_element_data.return_value = None
    _ensure_capacity(metadata, mock_coordinator)
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert sensor.native_value is None


@pytest.mark.parametrize("sensor_key", FORECAST_SENSOR_KEYS)
def test_element_sensor_native_value_empty_data(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
    sensor_key: str,
) -> None:
    """Test element sensor native value when underlying data is empty."""

    metadata = sensor_test_data[sensor_key]
    _ensure_capacity(metadata, mock_coordinator)
    mock_coordinator.get_element_data.return_value = {metadata.attribute_key: []}
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert sensor.native_value is None


@pytest.mark.parametrize("sensor_key", FORECAST_SENSOR_KEYS)
def test_element_sensor_extra_state_attributes(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
    sensor_key: str,
) -> None:
    """Test element sensor extra state attributes include forecast."""

    metadata = sensor_test_data[sensor_key]
    _ensure_capacity(metadata, mock_coordinator)
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)
    attrs = sensor.extra_state_attributes

    assert attrs is not None
    assert attrs["element_type"] == metadata.element_type
    assert "forecast" in attrs
    forecast = attrs["forecast"]
    assert isinstance(forecast, dict)
    assert len(forecast) == len(mock_coordinator.get_future_timestamps.return_value)


def test_coordinator_get_element_data_exception(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
) -> None:
    """Test that element sensors handle exceptions from coordinator."""

    metadata = sensor_test_data["power"]
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)
    assert sensor.native_value == -50.0

    mock_coordinator.get_element_data.side_effect = Exception("Data retrieval failed")
    sensor_error, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert sensor_error.native_value is None


def test_coordinator_get_future_timestamps_exception(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
) -> None:
    """Test element sensor attributes when timestamp retrieval fails."""

    metadata = sensor_test_data["power"]
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)
    attrs = sensor.extra_state_attributes
    assert attrs is not None
    assert "forecast" in attrs

    mock_coordinator.get_future_timestamps.side_effect = Exception("Timestamp retrieval failed")
    sensor_error, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)
    attrs_error = sensor_error.extra_state_attributes

    assert attrs_error is not None
    assert "forecast" not in attrs_error


def test_sensor_available_with_coordinator_exception(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
) -> None:
    """Test availability when coordinator raises exception."""

    metadata = sensor_test_data["power"]
    mock_coordinator.get_element_data.side_effect = Exception("Coordinator error")
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert sensor.available is False


def test_sensor_available_with_no_element_data(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
) -> None:
    """Test availability when no element data is returned."""

    metadata = sensor_test_data["power"]
    mock_coordinator.get_element_data.return_value = None
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert sensor.available is False


@pytest.mark.parametrize("sensor_key", OPTIMIZATION_SENSOR_KEYS)
def test_optimization_sensor_init(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
    sensor_key: str,
) -> None:
    """Test optimization sensor initialization."""

    metadata = sensor_test_data[sensor_key]
    sensor, subentry = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert sensor._attr_name == f"HAEO {metadata.element_name} {metadata.name_suffix}"
    assert sensor._attr_unique_id == f"{subentry.subentry_id}_{metadata.unique_suffix}"


def test_optimization_sensor_available_pending_status(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
) -> None:
    """Test optimization sensor availability with pending status."""

    metadata = sensor_test_data["optimization_cost"]
    mock_coordinator.optimization_result = None
    mock_coordinator.optimization_status = OPTIMIZATION_STATUS_PENDING
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert sensor.available is False


def test_optimization_sensor_available_with_results(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
) -> None:
    """Test optimization sensor availability with results."""

    metadata = sensor_test_data["optimization_cost"]
    mock_coordinator.optimization_result = {"cost": 100.0}
    mock_coordinator.optimization_status = OPTIMIZATION_STATUS_SUCCESS
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert sensor.available is True


def test_optimization_cost_sensor_native_value(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
) -> None:
    """Test optimization cost sensor native value."""

    metadata = sensor_test_data["optimization_cost"]
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert sensor.native_value == pytest.approx(15.50)


def test_optimization_cost_sensor_native_value_none(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
) -> None:
    """Test optimization cost sensor when no cost available."""

    metadata = sensor_test_data["optimization_cost"]
    mock_coordinator.last_optimization_cost = None
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert sensor.native_value is None


def test_optimization_status_sensor_native_value_success(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
) -> None:
    """Test optimization status sensor native value for success."""

    metadata = sensor_test_data["optimization_status"]
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert isinstance(sensor, HaeoOptimizationStatusSensor)
    assert sensor.native_value == OPTIMIZATION_STATUS_SUCCESS


def test_optimization_status_sensor_native_value_failure(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
) -> None:
    """Test optimization status sensor native value for failure."""

    metadata = sensor_test_data["optimization_status"]
    mock_coordinator.optimization_status = OPTIMIZATION_STATUS_FAILED
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert isinstance(sensor, HaeoOptimizationStatusSensor)
    assert sensor.native_value == OPTIMIZATION_STATUS_FAILED


def test_optimization_status_sensor_icon_success(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
) -> None:
    """Test optimization status sensor icon for success."""

    metadata = sensor_test_data["optimization_status"]
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert isinstance(sensor, HaeoOptimizationStatusSensor)
    assert sensor.icon == "mdi:check-circle"


def test_optimization_status_sensor_icon_failure(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
) -> None:
    """Test optimization status sensor icon for failure."""

    metadata = sensor_test_data["optimization_status"]
    mock_coordinator.optimization_status = OPTIMIZATION_STATUS_FAILED
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert isinstance(sensor, HaeoOptimizationStatusSensor)
    assert sensor.icon == "mdi:alert-circle"


def test_optimization_status_sensor_extra_state_attributes(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
) -> None:
    """Test optimization status sensor extra attributes."""

    metadata = sensor_test_data["optimization_status"]
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert isinstance(sensor, HaeoOptimizationStatusSensor)
    attrs = sensor.extra_state_attributes

    assert attrs is not None
    assert attrs["last_optimization"] == "2024-01-01T12:00:00+00:00"
    assert attrs["last_cost"] == 15.50
    assert attrs["last_duration_seconds"] == 7.5


def test_optimization_duration_sensor_native_value(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
) -> None:
    """Test optimization duration sensor native value."""

    metadata = sensor_test_data["optimization_duration"]
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert isinstance(sensor, HaeoOptimizationDurationSensor)
    assert sensor.native_value == pytest.approx(7.5)


def test_optimization_duration_sensor_extra_state_attributes(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
) -> None:
    """Test optimization duration sensor extra attributes."""

    metadata = sensor_test_data["optimization_duration"]
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert isinstance(sensor, HaeoOptimizationDurationSensor)
    attrs = sensor.extra_state_attributes

    assert attrs is not None
    assert attrs["last_optimization"] == "2024-01-01T12:00:00+00:00"
    assert attrs["optimization_status"] == OPTIMIZATION_STATUS_SUCCESS


def test_optimization_duration_sensor_disabled_by_default(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
) -> None:
    """Optimization duration sensor should be disabled by default."""

    metadata = sensor_test_data["optimization_duration"]
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert isinstance(sensor, HaeoOptimizationDurationSensor)
    assert sensor.entity_registry_enabled_default is False


def test_sensor_unavailable_when_sensor_data_missing(
    mock_config_entry: MockConfigEntry,
    mock_device_id: str,
    hass: HomeAssistant,
    subentry_factory: SubentryFactory,
) -> None:
    """Test sensors when coordinator has no data."""

    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.last_update_success = True
    coordinator.optimization_status = OPTIMIZATION_STATUS_FAILED
    coordinator.optimization_result = None
    coordinator.get_element_data = Mock(return_value=None)
    coordinator.get_future_timestamps = Mock(return_value=[])
    coordinator.config_entry = mock_config_entry
    coordinator.hass = hass
    coordinator.last_optimization_cost = None
    coordinator.last_optimization_duration = None
    coordinator.last_optimization_time = None

    element_subentry = subentry_factory("test_battery", ELEMENT_TYPE_BATTERY)
    power_sensor = HaeoPowerSensor(coordinator, element_subentry, "test_battery", ELEMENT_TYPE_BATTERY, mock_device_id)
    assert not power_sensor.available

    network_subentry = subentry_factory("network", ELEMENT_TYPE_NETWORK)
    status_sensor = HaeoOptimizationStatusSensor(coordinator, network_subentry, mock_device_id)
    assert status_sensor.available
    assert status_sensor.native_value == OPTIMIZATION_STATUS_FAILED


@pytest.mark.parametrize("sensor_key", FORECAST_SENSOR_KEYS)
def test_sensor_native_value_with_exception(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
    sensor_key: str,
) -> None:
    """Test sensors return None when data access raises exception."""

    metadata = sensor_test_data[sensor_key]
    mock_coordinator.get_element_data.side_effect = RuntimeError("Data access error")
    _ensure_capacity(metadata, mock_coordinator)
    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)

    assert sensor.native_value is None


@pytest.mark.parametrize("sensor_key", FORECAST_SENSOR_KEYS)
def test_sensor_extra_attributes_with_exception(
    mock_coordinator: Mock,
    mock_device_id: str,
    subentry_factory: SubentryFactory,
    sensor_test_data: dict[str, SensorTestData],
    sensor_key: str,
) -> None:
    """Test sensors handle timestamp exceptions in attributes."""

    metadata = sensor_test_data[sensor_key]
    _ensure_capacity(metadata, mock_coordinator)
    mock_coordinator.get_element_data.return_value = {metadata.attribute_key: [100.0, 200.0, 300.0]}
    mock_coordinator.get_future_timestamps.side_effect = RuntimeError("Timestamp error")

    sensor, _ = instantiate_sensor(metadata, mock_coordinator, subentry_factory, mock_device_id)
    attrs = sensor.extra_state_attributes

    assert attrs is not None
    assert "forecast" not in attrs


@pytest.mark.parametrize("sensor_type", SENSOR_TYPES)
async def test_sensor_name_translations(hass: HomeAssistant, sensor_type: str) -> None:
    """Test that sensor translations can be loaded."""

    translations = await async_get_translations(hass, "en", "entity", integrations=[DOMAIN])
    translation_key = f"component.{DOMAIN}.entity.sensor.{sensor_type}.name"
    assert translation_key in translations


@pytest.mark.parametrize("element_type", ELEMENT_TYPES)
async def test_device_name_translations(hass: HomeAssistant, element_type: str) -> None:
    """Test that device translations can be loaded."""

    translations = await async_get_translations(hass, "en", "device", integrations=[DOMAIN])
    translation_key = f"component.{DOMAIN}.device.{element_type}.name"
    assert translation_key in translations
