"""Tests for the HAEO output sensor entity."""

from dataclasses import replace
from datetime import UTC, datetime

# Coordinator output fixtures use runtime string keys that cannot satisfy the
# Literal key types of SubentryDevices.
from typing import Literal
from unittest.mock import Mock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceEntry
import pytest

from custom_components.haeo.const import CONF_RECORD_FORECASTS
from custom_components.haeo.coordinator import CoordinatorOutput, ForecastPoint
from custom_components.haeo.core.adapters.elements.battery import BATTERY_STATE_OF_CHARGE
from custom_components.haeo.core.adapters.elements.load import LOAD_POWER
from custom_components.haeo.core.data.loader.extractors.haeo import InterpolationMode
from custom_components.haeo.core.model import OutputData, OutputType
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.battery import ELEMENT_TYPE as BATTERY_TYPE
from custom_components.haeo.entities import HaeoSensor
from custom_components.haeo.entities.haeo_sensor import FORECAST_UNRECORDED_ATTRIBUTES
from custom_components.haeo.entities.tests.entity_helpers import mock_state_writes
from custom_components.haeo.entities.tests.sensor_helpers import (
    create_mock_coordinator,
    make_coordinator_data,
    make_output,
)


@pytest.fixture
def device_entry() -> DeviceEntry:
    """Return a mocked device entry instance."""
    device = Mock(spec=DeviceEntry)
    device.id = "mock-device"
    return device  # type: ignore[return-value]  # Mock(spec=DeviceEntry) is not a DeviceEntry for the type checker


def test_handle_coordinator_update_reapplies_metadata(device_entry: DeviceEntry) -> None:
    """Coordinator updates refresh metadata, forecasts, and native value."""

    coordinator = create_mock_coordinator()
    initial_output = make_output(
        type_=OutputType.POWER,
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
        device_key=ElementType.BATTERY,
        element_title="Battery",
        element_type=BATTERY_TYPE,
        output_name=LOAD_POWER,
        output_data=initial_output,
        unique_id="sensor-id",
    )
    mock_state_writes(sensor)

    forecast_time = datetime(2024, 1, 1, tzinfo=UTC)
    updated_output = make_output(
        type_=OutputType.POWER,
        unit="W",
        state=750.0,
        forecast=[ForecastPoint(time=forecast_time, value=750.0)],
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        options=None,
        interpolation_mode=InterpolationMode.PREVIOUS,
    )
    coordinator.data = make_coordinator_data({"battery": {"battery": {LOAD_POWER: updated_output}}})

    sensor._handle_coordinator_update()

    assert sensor.native_value == 750.0
    assert sensor.native_unit_of_measurement == "W"
    assert sensor.entity_category is EntityCategory.DIAGNOSTIC
    assert sensor.device_class is SensorDeviceClass.POWER
    assert sensor.state_class is SensorStateClass.MEASUREMENT
    assert sensor.options is None

    attributes = sensor.extra_state_attributes
    assert attributes is not None
    assert attributes["field_type"] == OutputType.POWER
    assert attributes["forecast"] == updated_output.forecast
    assert attributes["forecast"] is not updated_output.forecast
    assert attributes["interpolation_mode"] == InterpolationMode.PREVIOUS


def test_handle_coordinator_update_scales_percentage_outputs(device_entry: DeviceEntry) -> None:
    """Percentage outputs are scaled for display in sensors."""
    coordinator = create_mock_coordinator()
    forecast_time = datetime(2024, 1, 1, tzinfo=UTC)
    output = make_output(
        type_=OutputType.STATE_OF_CHARGE,
        unit="%",
        state=0.5,
        forecast=[ForecastPoint(time=forecast_time, value=0.5)],
        entity_category=None,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        options=None,
    )

    sensor = HaeoSensor(
        coordinator,
        device_entry=device_entry,
        subentry_key="battery",
        device_key=ElementType.BATTERY,
        element_title="Battery",
        element_type=BATTERY_TYPE,
        output_name=BATTERY_STATE_OF_CHARGE,
        output_data=output,
        unique_id="sensor-id",
    )
    mock_state_writes(sensor)

    coordinator.data = make_coordinator_data({"battery": {"battery": {BATTERY_STATE_OF_CHARGE: output}}})
    sensor._handle_coordinator_update()

    assert sensor.native_value == 50.0
    attributes = sensor.extra_state_attributes
    assert attributes is not None
    assert attributes["forecast"] == [{"time": forecast_time, "value": 50.0}]


@pytest.mark.parametrize(
    "coordinator_data",
    [
        pytest.param({}, id="no_data"),
        pytest.param({"battery": {"battery": {}}}, id="missing_output"),
        pytest.param({"battery": {}}, id="missing_device"),
    ],
)
def test_handle_coordinator_update_clears_value_when_missing_data(
    device_entry: DeviceEntry,
    coordinator_data: dict[str, dict[str, dict[str, OutputData]]],
) -> None:
    """Missing coordinator data clears the sensor value while keeping base attributes."""

    coordinator = create_mock_coordinator()
    initial_output = make_output(
        type_=OutputType.POWER,
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
        device_key=ElementType.BATTERY,
        element_title="Battery",
        element_type=BATTERY_TYPE,
        output_name=LOAD_POWER,
        output_data=initial_output,
        unique_id="sensor-id",
    )
    mock_state_writes(sensor)

    coordinator.data = make_coordinator_data(coordinator_data)
    sensor._handle_coordinator_update()

    assert sensor.native_value is None
    attributes = sensor.extra_state_attributes
    assert attributes == {
        "element_name": "Battery",
        "element_type": BATTERY_TYPE,
        "output_name": LOAD_POWER,
        "field_type": OutputType.POWER,
        "source_role": "output",
        "advanced": False,
    }


def test_sensor_availability_follows_coordinator(device_entry: DeviceEntry) -> None:
    """Sensor availability mirrors the coordinator's update status."""

    coordinator = create_mock_coordinator()
    output = make_output(
        type_=OutputType.POWER,
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
        device_key=ElementType.BATTERY,
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

    coordinator = create_mock_coordinator()
    output = make_output(
        type_=OutputType.POWER,
        unit="kW",
        state=1.0,
        forecast=None,
        entity_category=None,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        options=None,
    )
    coordinator.data = make_coordinator_data({"battery": {"battery": {LOAD_POWER: output}}})

    sensor = HaeoSensor(
        coordinator,
        device_entry=device_entry,
        subentry_key="battery",
        device_key=ElementType.BATTERY,
        element_title="Battery",
        element_type=BATTERY_TYPE,
        output_name=LOAD_POWER,
        output_data=output,
        unique_id="sensor-id",
    )

    sensor._handle_coordinator_update = Mock()

    await sensor.async_added_to_hass()

    sensor._handle_coordinator_update.assert_called_once()


def test_handle_coordinator_update_sets_direction(device_entry: DeviceEntry) -> None:
    """Coordinator updates apply the direction attribute."""
    coordinator = create_mock_coordinator()
    initial_output = make_output(
        type_=OutputType.POWER,
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
        device_key=ElementType.BATTERY,
        element_title="Battery",
        element_type=BATTERY_TYPE,
        output_name=LOAD_POWER,
        output_data=initial_output,
        unique_id="sensor-id",
    )
    mock_state_writes(sensor)

    updated_output = make_output(
        type_=OutputType.POWER,
        unit="kW",
        state=1.0,
        forecast=None,
        entity_category=None,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        options=None,
        direction="+",
    )
    coordinator.data = make_coordinator_data({"battery": {"battery": {LOAD_POWER: updated_output}}})

    sensor._handle_coordinator_update()

    attributes = sensor.extra_state_attributes
    assert attributes is not None
    assert attributes["direction"] == "+"


@pytest.mark.parametrize(
    ("record_forecasts", "expect_unrecorded"),
    [
        (False, True),  # Default: forecasts are excluded from recorder
        (True, False),  # When enabled: forecasts are recorded
    ],
)
def test_unrecorded_attributes_based_on_config(
    device_entry: DeviceEntry,
    record_forecasts: bool,
    expect_unrecorded: bool,
) -> None:
    """Sensor applies recorder filtering based on record_forecasts config."""
    coordinator = create_mock_coordinator()
    # Mock the config_entry.data.get behavior
    coordinator.config_entry = Mock()
    coordinator.config_entry.data = {CONF_RECORD_FORECASTS: record_forecasts}

    output = make_output(
        type_=OutputType.POWER,
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
        device_key=ElementType.BATTERY,
        element_title="Battery",
        element_type=BATTERY_TYPE,
        output_name=LOAD_POWER,
        output_data=output,
        unique_id="sensor-id",
    )

    sensor._state_info = {"unrecorded_attributes": frozenset()}
    sensor._apply_recorder_attribute_filtering()
    if expect_unrecorded:
        assert sensor._state_info["unrecorded_attributes"] == FORECAST_UNRECORDED_ATTRIBUTES
    else:
        assert sensor._state_info["unrecorded_attributes"] == frozenset()


def test_handle_coordinator_update_sets_fixed_attribute(device_entry: DeviceEntry) -> None:
    """Fixed outputs expose a fixed=True attribute for the frontend card."""
    coordinator = create_mock_coordinator()
    initial_output = make_output(
        type_=OutputType.POWER,
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
        subentry_key="load",
        device_key=ElementType.LOAD,
        element_title="Load",
        element_type="load",
        output_name=LOAD_POWER,
        output_data=initial_output,
        unique_id="sensor-id",
    )
    mock_state_writes(sensor)

    fixed_output = CoordinatorOutput(
        type=OutputType.POWER,
        unit="kW",
        state=2.0,
        forecast=[ForecastPoint(time=datetime.now(tz=UTC), value=2.0)],
        direction="-",
        entity_category=None,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        options=None,
        fixed=True,
    )
    coordinator.data = make_coordinator_data({"load": {"load": {LOAD_POWER: fixed_output}}})

    sensor._handle_coordinator_update()

    attributes = sensor.extra_state_attributes
    assert attributes is not None
    assert attributes["fixed"] is True


@pytest.mark.parametrize("direction", ["+", "-", None])
def test_handle_coordinator_update_sets_state_of_charge_direction(
    device_entry: DeviceEntry, direction: Literal["+", "-"] | None
) -> None:
    """A state of charge line exposes the flow it holds the batteries ready for, and a plain one has no direction."""
    coordinator = create_mock_coordinator()
    output = make_output(
        type_=OutputType.STATE_OF_CHARGE,
        unit="%",
        state=0.5,
        forecast=None,
        entity_category=None,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        options=None,
    )
    sensor = HaeoSensor(
        coordinator,
        device_entry=device_entry,
        subentry_key="buffer",
        device_key=ElementType.BUFFER,
        element_title="Backup",
        element_type=ElementType.BUFFER,
        output_name=LOAD_POWER,
        output_data=output,
        unique_id="sensor-id",
    )
    mock_state_writes(sensor)
    coordinator.data = make_coordinator_data({"buffer": {"buffer": {LOAD_POWER: replace(output, direction=direction)}}})

    sensor._handle_coordinator_update()

    attributes = sensor.extra_state_attributes
    assert attributes is not None
    assert attributes.get("direction") == direction
    assert ("direction" in attributes) is (direction is not None)


@pytest.mark.parametrize(("advanced", "enabled_default"), [(True, False), (False, True)])
def test_advanced_outputs_are_disabled_by_default(
    device_entry: DeviceEntry,
    *,
    advanced: bool,
    enabled_default: bool,
) -> None:
    """Sensors for advanced outputs ship disabled in the entity registry."""
    output = replace(
        make_output(
            type_=OutputType.SHADOW_PRICE,
            unit="$/kWh",
            state=0.0,
            forecast=None,
            entity_category=None,
            device_class=None,
            state_class=None,
            options=None,
        ),
        advanced=advanced,
    )

    sensor = HaeoSensor(
        create_mock_coordinator(),
        device_entry=device_entry,
        subentry_key="battery",
        device_key=ElementType.BATTERY,
        element_title="Battery",
        element_type=BATTERY_TYPE,
        output_name=LOAD_POWER,
        output_data=output,
        unique_id="sensor-id",
    )

    assert sensor.entity_registry_enabled_default is enabled_default
