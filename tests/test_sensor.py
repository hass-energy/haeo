"""Tests for the HAEO sensor platform."""

from datetime import UTC, datetime
from types import MappingProxyType
from typing import Literal, cast
from unittest.mock import Mock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import (
    CONF_ELEMENT_TYPE,
    CONF_NAME,
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
    OUTPUT_NAME_OPTIMIZATION_DURATION,
    OUTPUT_NAME_OPTIMIZATION_STATUS,
)
from custom_components.haeo.coordinator import CoordinatorOutput, ForecastPoint
from custom_components.haeo.elements.battery import ELEMENT_TYPE as BATTERY_TYPE
from custom_components.haeo.elements.load import LOAD_POWER
from custom_components.haeo.entities import HaeoHorizonEntity, HaeoSensor
from custom_components.haeo.model import OUTPUT_TYPE_DURATION, OUTPUT_TYPE_POWER, OUTPUT_TYPE_STATUS, OutputType
from custom_components.haeo.sensor import async_setup_entry


def _create_mock_coordinator() -> Mock:
    """Create a mock coordinator for sensor tests.

    Returns a Mock configured with the minimal interface needed for sensor tests.
    Callers can use this where HaeoDataUpdateCoordinator is expected since Mock
    attribute access returns Any, making it compatible at runtime.
    """
    coordinator = Mock()
    coordinator.data = {}
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    return coordinator


def _make_output(
    *,
    type_: OutputType,
    unit: str | None,
    state: float | str | None,
    forecast: list[ForecastPoint] | None,
    entity_category: EntityCategory | None,
    device_class: SensorDeviceClass | None,
    state_class: SensorStateClass | None,
    options: tuple[str, ...] | None,
    direction: Literal["+", "-"] | None = None,
) -> CoordinatorOutput:
    return CoordinatorOutput(
        type=type_,
        unit=unit,
        state=state,
        forecast=forecast,
        entity_category=entity_category,
        device_class=device_class,
        state_class=state_class,
        options=options,
        direction=direction,
    )


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a config entry configured for the sensor platform tests."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Mock Network",
        data={
            "name": "Mock Network",
            "tier_1_count": 5,
            "tier_1_duration": 1,
            "tier_2_count": 11,
            "tier_2_duration": 5,
            "tier_3_count": 0,
            "tier_3_duration": 30,
            "tier_4_count": 0,
            "tier_4_duration": 60,
        },
        entry_id="mock_entry",
    )
    entry.add_to_hass(hass)

    network_subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: ELEMENT_TYPE_NETWORK, CONF_NAME: entry.title}),
        subentry_type=ELEMENT_TYPE_NETWORK,
        title=entry.title,
        unique_id=None,
    )
    battery_subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: BATTERY_TYPE, CONF_NAME: "Battery"}),
        subentry_type=BATTERY_TYPE,
        title="Battery",
        unique_id=None,
    )

    hass.config_entries.async_add_subentry(entry, network_subentry)
    hass.config_entries.async_add_subentry(entry, battery_subentry)

    return entry


@pytest.fixture
def device_entry() -> DeviceEntry:
    """Return a mocked device entry instance."""
    device = Mock(spec=DeviceEntry)
    device.id = "mock-device"
    return cast("DeviceEntry", device)


async def test_async_setup_entry_creates_sensors_with_metadata(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Sensors inherit metadata supplied by coordinator outputs."""

    coordinator = _create_mock_coordinator()
    network_key = config_entry.title
    battery_key = "Battery"

    coordinator.data = {
        network_key: {
            network_key: {
                OUTPUT_NAME_OPTIMIZATION_STATUS: _make_output(
                    type_=OUTPUT_TYPE_STATUS,
                    unit=None,
                    state="pending",
                    forecast=None,
                    entity_category=None,
                    device_class=SensorDeviceClass.ENUM,
                    state_class=None,
                    options=("failed", "pending", "success"),
                ),
                OUTPUT_NAME_OPTIMIZATION_DURATION: _make_output(
                    type_=OUTPUT_TYPE_DURATION,
                    unit=UnitOfTime.SECONDS,
                    state=12.3,
                    forecast=None,
                    entity_category=EntityCategory.DIAGNOSTIC,
                    device_class=SensorDeviceClass.DURATION,
                    state_class=SensorStateClass.MEASUREMENT,
                    options=None,
                ),
            },
        },
        battery_key: {
            battery_key: {
                LOAD_POWER: _make_output(
                    type_=OUTPUT_TYPE_POWER,
                    unit="kW",
                    state=1.5,
                    forecast=[ForecastPoint(time=datetime.now(tz=UTC), value=1.5)],
                    entity_category=None,
                    device_class=SensorDeviceClass.POWER,
                    state_class=SensorStateClass.MEASUREMENT,
                    options=None,
                )
            },
        },
    }
    config_entry.runtime_data = HaeoRuntimeData(coordinator=coordinator)

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_called_once()
    sensors = list(async_add_entities.call_args.args[0])
    # 3 output sensors + 1 horizon entity = 4 total
    assert len(sensors) == 4

    status_sensor = next(sensor for sensor in sensors if sensor.translation_key == OUTPUT_NAME_OPTIMIZATION_STATUS)
    assert status_sensor.device_class is SensorDeviceClass.ENUM
    assert status_sensor.options == ["failed", "pending", "success"]
    assert status_sensor.native_value == "pending"

    duration_sensor = next(sensor for sensor in sensors if sensor.translation_key == OUTPUT_NAME_OPTIMIZATION_DURATION)
    assert duration_sensor.entity_category is EntityCategory.DIAGNOSTIC
    assert duration_sensor.device_class is SensorDeviceClass.DURATION
    assert duration_sensor.state_class is SensorStateClass.MEASUREMENT

    power_sensor = next(sensor for sensor in sensors if sensor.translation_key == LOAD_POWER)
    assert power_sensor.native_unit_of_measurement == "kW"
    assert power_sensor.device_class is SensorDeviceClass.POWER
    assert power_sensor.state_class is SensorStateClass.MEASUREMENT


async def test_async_setup_entry_raises_when_runtime_data_missing(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Setup should raise RuntimeError when runtime data is not set.

    This indicates a programming error - __init__.py must set runtime_data
    before platforms are set up.
    """
    config_entry.runtime_data = None
    async_add_entities = Mock()

    with pytest.raises(RuntimeError, match="Runtime data not set"):
        await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_not_called()


async def test_async_setup_entry_creates_horizon_when_no_outputs(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Horizon entity is created even when coordinator data is empty.

    The horizon entity is essential for input entities to function,
    so it must be created regardless of optimization output availability.
    """
    coordinator = _create_mock_coordinator()
    coordinator.data = {}
    config_entry.runtime_data = HaeoRuntimeData(coordinator=coordinator)

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    # Horizon entity is always created for network subentry
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], HaeoHorizonEntity)


def test_handle_coordinator_update_reapplies_metadata(device_entry: DeviceEntry) -> None:
    """Coordinator updates refresh metadata, forecasts, and native value."""

    coordinator = _create_mock_coordinator()
    initial_output = _make_output(
        type_=OUTPUT_TYPE_POWER,
        unit="kW",
        state=1.0,
        forecast=None,
        entity_category=None,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        options=None,
    )

    sensor = HaeoSensor(
        coordinator,
        device_entry=device_entry,
        subentry_key="battery",
        device_key="battery",
        element_title="Battery",
        element_type=BATTERY_TYPE,
        output_name=LOAD_POWER,
        output_data=initial_output,
        unique_id="sensor-id",
    )
    sensor.async_write_ha_state = Mock()

    forecast_time = datetime(2024, 1, 1, tzinfo=UTC)
    updated_output = _make_output(
        type_=OUTPUT_TYPE_POWER,
        unit="W",
        state=750.0,
        forecast=[ForecastPoint(time=forecast_time, value=750.0)],
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        options=None,
    )
    coordinator.data = {"battery": {"battery": {LOAD_POWER: updated_output}}}

    sensor._handle_coordinator_update()

    assert sensor.native_value == 750.0
    assert sensor.native_unit_of_measurement == "W"
    assert sensor.entity_category is EntityCategory.DIAGNOSTIC
    assert sensor.device_class is SensorDeviceClass.POWER
    assert sensor.state_class is SensorStateClass.MEASUREMENT
    assert sensor.options is None

    attributes = sensor.extra_state_attributes
    assert attributes is not None
    assert attributes["output_type"] == OUTPUT_TYPE_POWER
    assert attributes["forecast"] == updated_output.forecast
    assert attributes["forecast"] is not updated_output.forecast


def test_handle_coordinator_update_without_data_leaves_sensor_empty(device_entry: DeviceEntry) -> None:
    """Missing coordinator data clears the sensor value while keeping base attributes."""

    coordinator = _create_mock_coordinator()
    initial_output = _make_output(
        type_=OUTPUT_TYPE_POWER,
        unit="kW",
        state=5.0,
        forecast=None,
        entity_category=None,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        options=None,
    )

    sensor = HaeoSensor(
        coordinator,
        device_entry=device_entry,
        subentry_key="battery",
        device_key="battery",
        element_title="Battery",
        element_type=BATTERY_TYPE,
        output_name=LOAD_POWER,
        output_data=initial_output,
        unique_id="sensor-id",
    )
    sensor.async_write_ha_state = Mock()

    coordinator.data = {}
    sensor._handle_coordinator_update()

    assert sensor.native_value is None
    attributes = sensor.extra_state_attributes
    assert attributes == {
        "element_name": "Battery",
        "element_type": BATTERY_TYPE,
        "output_name": LOAD_POWER,
        "output_type": OUTPUT_TYPE_POWER,
        "advanced": False,
    }


def test_sensor_availability_follows_coordinator(device_entry: DeviceEntry) -> None:
    """Sensor availability mirrors the coordinator's update status."""

    coordinator = _create_mock_coordinator()
    output = _make_output(
        type_=OUTPUT_TYPE_POWER,
        unit="kW",
        state=1.0,
        forecast=None,
        entity_category=None,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        options=None,
    )

    sensor = HaeoSensor(
        coordinator,
        device_entry=device_entry,
        subentry_key="battery",
        device_key="battery",
        element_title="Battery",
        element_type=BATTERY_TYPE,
        output_name=LOAD_POWER,
        output_data=output,
        unique_id="sensor-id",
    )

    coordinator.last_update_success = True
    assert sensor.available is True

    coordinator.last_update_success = False
    assert sensor.available is False


async def test_sensor_async_added_to_hass_runs_initial_update(device_entry: DeviceEntry) -> None:
    """async_added_to_hass should trigger an initial update when data exists."""

    coordinator = _create_mock_coordinator()
    output = _make_output(
        type_=OUTPUT_TYPE_POWER,
        unit="kW",
        state=1.0,
        forecast=None,
        entity_category=None,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        options=None,
    )
    coordinator.data = {"battery": {"battery": {LOAD_POWER: output}}}

    sensor = HaeoSensor(
        coordinator,
        device_entry=device_entry,
        subentry_key="battery",
        device_key="battery",
        element_title="Battery",
        element_type=BATTERY_TYPE,
        output_name=LOAD_POWER,
        output_data=output,
        unique_id="sensor-id",
    )

    sensor._handle_coordinator_update = Mock()

    await sensor.async_added_to_hass()

    sensor._handle_coordinator_update.assert_called_once()


async def test_async_setup_entry_creates_sub_device_sensors(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Sensors are created for sub-devices (e.g. nested components)."""

    coordinator = _create_mock_coordinator()
    battery_key = "Battery"
    sub_device_key = "Battery Sub"

    coordinator.data = {
        battery_key: {
            sub_device_key: {
                LOAD_POWER: _make_output(
                    type_=OUTPUT_TYPE_POWER,
                    unit="kW",
                    state=1.0,
                    forecast=None,
                    entity_category=None,
                    device_class=SensorDeviceClass.POWER,
                    state_class=SensorStateClass.MEASUREMENT,
                    options=None,
                )
            },
        },
    }
    config_entry.runtime_data = HaeoRuntimeData(coordinator=coordinator)

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_called_once()
    sensors = list(async_add_entities.call_args.args[0])
    # 2 entities: horizon entity + 1 output sensor
    assert len(sensors) == 2

    # Find the output sensor (not the horizon entity)
    output_sensors = [s for s in sensors if isinstance(s, HaeoSensor)]
    assert len(output_sensors) == 1

    sensor = output_sensors[0]
    # Check that the sensor uses the output name as translation key (consistent with all sensors)
    assert sensor.translation_key == LOAD_POWER
    # Check that it's associated with the correct sub-device
    assert sensor._device_key == sub_device_key


def test_handle_coordinator_update_sets_direction(device_entry: DeviceEntry) -> None:
    """Coordinator updates apply the direction attribute."""
    coordinator = _create_mock_coordinator()
    initial_output = _make_output(
        type_=OUTPUT_TYPE_POWER,
        unit="kW",
        state=1.0,
        forecast=None,
        entity_category=None,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        options=None,
    )

    sensor = HaeoSensor(
        coordinator,
        device_entry=device_entry,
        subentry_key="battery",
        device_key="battery",
        element_title="Battery",
        element_type=BATTERY_TYPE,
        output_name=LOAD_POWER,
        output_data=initial_output,
        unique_id="sensor-id",
    )
    sensor.async_write_ha_state = Mock()

    updated_output = _make_output(
        type_=OUTPUT_TYPE_POWER,
        unit="kW",
        state=1.0,
        forecast=None,
        entity_category=None,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        options=None,
        direction="+",
    )
    coordinator.data = {"battery": {"battery": {LOAD_POWER: updated_output}}}

    sensor._handle_coordinator_update()

    attributes = sensor.extra_state_attributes
    assert attributes is not None
    assert attributes["direction"] == "+"


def test_handle_coordinator_update_missing_output_clears_value(device_entry: DeviceEntry) -> None:
    """If the specific output is missing from data, sensor value is cleared."""
    coordinator = _create_mock_coordinator()
    initial_output = _make_output(
        type_=OUTPUT_TYPE_POWER,
        unit="kW",
        state=1.0,
        forecast=None,
        entity_category=None,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        options=None,
    )

    sensor = HaeoSensor(
        coordinator,
        device_entry=device_entry,
        subentry_key="battery",
        device_key="battery",
        element_title="Battery",
        element_type=BATTERY_TYPE,
        output_name=LOAD_POWER,
        output_data=initial_output,
        unique_id="sensor-id",
    )
    sensor.async_write_ha_state = Mock()

    # Case 1: Subentry exists, device exists, but output missing
    coordinator.data = {"battery": {"battery": {}}}
    sensor._handle_coordinator_update()
    assert sensor.native_value is None

    # Reset
    sensor._apply_output(initial_output)

    # Case 2: Subentry exists, device missing
    coordinator.data = {"battery": {}}
    sensor._handle_coordinator_update()
    assert sensor.native_value is None
