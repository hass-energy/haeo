"""Tests for the HAEO sensor platform."""

from collections.abc import Callable
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
from custom_components.haeo.coordinator_network import CoordinatorOutput, ForecastPoint, HaeoDataUpdateCoordinator
from custom_components.haeo.elements.battery import ELEMENT_TYPE as BATTERY_TYPE
from custom_components.haeo.elements.load import LOAD_POWER
from custom_components.haeo.model import OUTPUT_TYPE_DURATION, OUTPUT_TYPE_POWER, OUTPUT_TYPE_STATUS, OutputType
from custom_components.haeo.sensors import async_setup_entry
from custom_components.haeo.sensors.sensor import HaeoSensor


class _DummyCoordinator:
    """Minimal coordinator stub for sensor tests."""

    def __init__(self) -> None:
        self.data: dict[str, dict[str, dict[str, CoordinatorOutput]]] = {}
        self.last_update_success = True
        self._listeners: list[Callable[[], None]] = []

    def async_add_listener(
        self, update_callback: Callable[[], None], _context: object | None = None
    ) -> Callable[[], None]:
        """Register a listener and return an unsubscribe callback."""
        self._listeners.append(update_callback)
        return lambda: None


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
        data={"name": "Mock Network", "horizon_hours": 1, "period_minutes": 5},
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

    coordinator = _DummyCoordinator()
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
    config_entry.runtime_data = HaeoRuntimeData(
        network_coordinator=coordinator,
        element_coordinators={},
    )

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_called_once()
    sensors = list(async_add_entities.call_args.args[0])
    assert len(sensors) == 3

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


async def test_async_setup_entry_ignores_missing_coordinator(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Setup should no-op when the config entry lacks runtime data."""

    config_entry.runtime_data = None
    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_not_called()


async def test_async_setup_entry_skips_when_no_outputs(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """No entities are created when coordinator data is empty."""

    coordinator = _DummyCoordinator()
    coordinator.data = {}
    config_entry.runtime_data = HaeoRuntimeData(
        network_coordinator=coordinator,
        element_coordinators={},
    )

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_not_called()


def test_handle_coordinator_update_reapplies_metadata(device_entry: DeviceEntry) -> None:
    """Coordinator updates refresh metadata, forecasts, and native value."""

    coordinator = _DummyCoordinator()
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
        cast("HaeoDataUpdateCoordinator", coordinator),
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

    coordinator = _DummyCoordinator()
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
        cast("HaeoDataUpdateCoordinator", coordinator),
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

    coordinator = _DummyCoordinator()
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
        cast("HaeoDataUpdateCoordinator", coordinator),
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

    coordinator = _DummyCoordinator()
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
        cast("HaeoDataUpdateCoordinator", coordinator),
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

    coordinator = _DummyCoordinator()
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
    config_entry.runtime_data = HaeoRuntimeData(
        network_coordinator=coordinator,
        element_coordinators={},
    )

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_called_once()
    sensors = list(async_add_entities.call_args.args[0])
    assert len(sensors) == 1

    sensor = sensors[0]
    # Check that the sensor uses the output name as translation key (consistent with all sensors)
    assert sensor.translation_key == LOAD_POWER
    # Check that it's associated with the correct sub-device
    assert sensor._device_key == sub_device_key


def test_handle_coordinator_update_sets_direction(device_entry: DeviceEntry) -> None:
    """Coordinator updates apply the direction attribute."""
    coordinator = _DummyCoordinator()
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
        cast("HaeoDataUpdateCoordinator", coordinator),
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
    coordinator = _DummyCoordinator()
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
        cast("HaeoDataUpdateCoordinator", coordinator),
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
