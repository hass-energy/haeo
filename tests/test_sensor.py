"""Test the HAEO sensor platform."""

from datetime import UTC, datetime
from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN, ELEMENT_TYPE_NETWORK
from custom_components.haeo.coordinator import CoordinatorOutput
from custom_components.haeo.elements.battery import ELEMENT_TYPE as BATTERY_TYPE
from custom_components.haeo.model import (
    OUTPUT_NAME_OPTIMIZATION_COST,
    OUTPUT_NAME_POWER_CONSUMED,
    OUTPUT_TYPE_COST,
    OUTPUT_TYPE_POWER,
)
from custom_components.haeo.sensors import HaeoSensor, async_setup_entry


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a config entry for the sensors under test."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test HAEO",
        data={
            "name": "Test HAEO",
            "horizon_hours": 24,
            "period_minutes": 5,
        },
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def device_entry() -> Mock:
    """Provide a mock device entry."""
    device = Mock(spec=DeviceEntry)
    device.id = "test_device_id"
    return device


@pytest.fixture
def coordinator() -> Mock:
    """Provide a minimal coordinator implementation for sensors."""

    coordinator = Mock()
    coordinator.data = {}
    coordinator.last_update_success = True
    coordinator.last_optimization_cost = None
    coordinator.last_optimization_duration = None
    coordinator.last_optimization_time = None
    coordinator.optimization_status = "pending"
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    coordinator.async_update_data = Mock()
    coordinator.async_request_refresh = Mock()
    return coordinator


async def test_async_setup_entry_creates_sensors(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    coordinator: Mock,
) -> None:
    """Sensors are created for all outputs in coordinator data."""

    # Set up subentries for "network" and "battery"
    network_subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: ELEMENT_TYPE_NETWORK, CONF_NAME: config_entry.title}),
        subentry_type=ELEMENT_TYPE_NETWORK,
        title=config_entry.title,
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(config_entry, network_subentry)

    battery_subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: BATTERY_TYPE, CONF_NAME: "Battery Storage"}),
        subentry_type=BATTERY_TYPE,
        title="Battery Storage",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(config_entry, battery_subentry)

    coordinator.data = {
        "test_haeo": {
            OUTPUT_NAME_OPTIMIZATION_COST: CoordinatorOutput(
                type=OUTPUT_TYPE_COST,
                unit="$",
                state=12.5,
                forecast=None,
            ),
        },
        "battery_storage": {
            OUTPUT_NAME_POWER_CONSUMED: CoordinatorOutput(
                type=OUTPUT_TYPE_POWER,
                unit="kW",
                state=1.0,
                forecast=None,
            ),
        },
    }
    config_entry.runtime_data = coordinator

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_called_once()
    sensors = async_add_entities.call_args.args[0]
    assert len(sensors) == 2

    unique_ids = {sensor.unique_id for sensor in sensors}
    assert unique_ids == {
        f"{config_entry.entry_id}_{network_subentry.subentry_id}_{OUTPUT_NAME_OPTIMIZATION_COST}",
        f"{config_entry.entry_id}_{battery_subentry.subentry_id}_{OUTPUT_NAME_POWER_CONSUMED}",
    }

    translation_keys = {sensor.translation_key for sensor in sensors}
    assert translation_keys == {OUTPUT_NAME_OPTIMIZATION_COST, OUTPUT_NAME_POWER_CONSUMED}


async def test_async_setup_entry_skips_without_data(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    coordinator: Mock,
) -> None:
    """No sensors are created when coordinator exposes no outputs."""

    coordinator.data = {}
    config_entry.runtime_data = coordinator

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_not_called()


async def test_async_setup_entry_skips_without_coordinator(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """No sensors are created when coordinator is not available."""

    config_entry.runtime_data = None

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_not_called()


async def test_async_setup_entry_skips_empty_element_outputs(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    coordinator: Mock,
) -> None:
    """Elements with empty output dicts are skipped."""

    # Set up subentries for "network" and "battery"
    network_subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: ELEMENT_TYPE_NETWORK, CONF_NAME: config_entry.title}),
        subentry_type=ELEMENT_TYPE_NETWORK,
        title=config_entry.title,
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(config_entry, network_subentry)

    battery_subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: BATTERY_TYPE, CONF_NAME: "Battery Storage"}),
        subentry_type=BATTERY_TYPE,
        title="Battery Storage",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(config_entry, battery_subentry)

    coordinator.data = {
        "battery_storage": {},  # Empty outputs
        "test_haeo": {
            OUTPUT_NAME_OPTIMIZATION_COST: CoordinatorOutput(
                type=OUTPUT_TYPE_COST,
                unit="$",
                state=0.5,
                forecast=None,
            )
        },  # Has outputs
    }
    config_entry.runtime_data = coordinator

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    # Only network sensor should be created
    async_add_entities.assert_called_once()
    sensors = async_add_entities.call_args.args[0]
    assert len(sensors) == 1
    expected_id = f"{config_entry.entry_id}_{network_subentry.subentry_id}_{OUTPUT_NAME_OPTIMIZATION_COST}"
    assert sensors[0].unique_id == expected_id


def test_sensor_native_value_returns_first_value(coordinator: Mock, device_entry: Mock) -> None:
    """The first value in the output series becomes the sensor reading."""

    output_data = CoordinatorOutput(OUTPUT_TYPE_POWER, "kW", 3.5, forecast=None)
    coordinator.data = {"battery": {OUTPUT_NAME_POWER_CONSUMED: output_data}}

    sensor = HaeoSensor(
        coordinator,
        device_entry=device_entry,
        element_key="battery",
        element_title="Battery",
        element_type=BATTERY_TYPE,
        output_name=OUTPUT_NAME_POWER_CONSUMED,
        output_data=output_data,
        unique_id="unique-id",
    )
    sensor.async_write_ha_state = Mock()

    sensor._handle_coordinator_update()

    assert sensor.native_value == 3.5


def test_sensor_native_value_handles_missing_data(coordinator: Mock, device_entry: Mock) -> None:
    """Sensors return None when the coordinator has no data for them."""

    output_data = CoordinatorOutput(OUTPUT_TYPE_POWER, "kW", 3.5, forecast=None)
    coordinator.data = {}

    sensor = HaeoSensor(
        coordinator,
        device_entry=device_entry,
        element_key="battery",
        element_title="Battery",
        element_type=BATTERY_TYPE,
        output_name=OUTPUT_NAME_POWER_CONSUMED,
        output_data=output_data,
        unique_id="unique-id",
    )
    sensor.async_write_ha_state = Mock()

    sensor._handle_coordinator_update()

    assert sensor.native_value is None


def test_extra_state_attributes_include_forecast(coordinator: Mock, device_entry: Mock) -> None:
    """Forecast values beyond the first datapoint are exposed."""

    base_timestamp = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp())
    forecast = {
        datetime.fromtimestamp(base_timestamp, tz=UTC).isoformat(): 10.0,
        datetime.fromtimestamp(base_timestamp + 3600, tz=UTC).isoformat(): 11.0,
        datetime.fromtimestamp(base_timestamp + 7200, tz=UTC).isoformat(): 12.0,
    }
    output_data = CoordinatorOutput(OUTPUT_TYPE_COST, "USD", 10.0, forecast=forecast)
    coordinator.data = {"test_haeo": {OUTPUT_NAME_OPTIMIZATION_COST: output_data}}

    sensor = HaeoSensor(
        coordinator,
        device_entry=device_entry,
        element_key="test_haeo",
        element_title="Test HAEO",
        element_type=ELEMENT_TYPE_NETWORK,
        output_name=OUTPUT_NAME_OPTIMIZATION_COST,
        output_data=output_data,
        unique_id="cost-id",
    )
    sensor.async_write_ha_state = Mock()

    sensor._handle_coordinator_update()

    attrs = sensor.extra_state_attributes
    assert attrs is not None
    assert attrs["forecast"] == forecast
    assert attrs["output_name"] == OUTPUT_NAME_OPTIMIZATION_COST
    assert attrs["output_type"] == OUTPUT_TYPE_COST


def test_extra_state_attributes_empty_when_no_data(coordinator: Mock, device_entry: Mock) -> None:
    """Sensors expose no extra attributes when coordinator has no data."""

    output_data = CoordinatorOutput(OUTPUT_TYPE_POWER, "kW", 1.0, forecast=None)
    coordinator.data = {}

    sensor = HaeoSensor(
        coordinator,
        device_entry=device_entry,
        element_key="battery",
        element_title="Battery",
        element_type=BATTERY_TYPE,
        output_name=OUTPUT_NAME_POWER_CONSUMED,
        output_data=output_data,
        unique_id="power-id",
    )
    sensor.async_write_ha_state = Mock()

    sensor._handle_coordinator_update()

    attrs = sensor.extra_state_attributes
    assert attrs is not None
    assert attrs == {
        "element_name": "Battery",
        "element_type": BATTERY_TYPE,
        "output_name": OUTPUT_NAME_POWER_CONSUMED,
        "output_type": OUTPUT_TYPE_POWER,
    }


def test_sensor_availability_tracks_coordinator_status(coordinator: Mock, device_entry: Mock) -> None:
    """Availability mirrors the coordinator's last update success flag."""

    output_data = CoordinatorOutput(OUTPUT_TYPE_COST, "USD", 5.0, forecast=None)
    coordinator.data = {"test_haeo": {OUTPUT_NAME_OPTIMIZATION_COST: output_data}}

    sensor = HaeoSensor(
        coordinator,
        device_entry=device_entry,
        element_key="test_haeo",
        element_title="Test HAEO",
        element_type=ELEMENT_TYPE_NETWORK,
        output_name=OUTPUT_NAME_OPTIMIZATION_COST,
        output_data=output_data,
        unique_id="availability-id",
    )

    coordinator.last_update_success = True
    assert sensor.available is True

    coordinator.last_update_success = False
    assert sensor.available is False


def test_sensor_handles_forecast_timestamps(coordinator: Mock, device_entry: Mock) -> None:
    """Coordinator timestamps do not affect sensor readings."""

    coordinator.last_optimization_time = datetime.now(tz=UTC)
    output_data = CoordinatorOutput(OUTPUT_TYPE_COST, "USD", 6.0, forecast=None)
    coordinator.data = {"test_haeo": {OUTPUT_NAME_OPTIMIZATION_COST: output_data}}

    sensor = HaeoSensor(
        coordinator,
        device_entry=device_entry,
        element_key="test_haeo",
        element_title="Test HAEO",
        element_type=ELEMENT_TYPE_NETWORK,
        output_name=OUTPUT_NAME_OPTIMIZATION_COST,
        output_data=output_data,
        unique_id="timestamp-id",
    )
    sensor.async_write_ha_state = Mock()

    sensor._handle_coordinator_update()

    assert sensor.native_value == 6.0
