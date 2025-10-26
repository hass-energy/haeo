"""Test the HAEO sensor platform."""

from datetime import UTC, datetime
from unittest.mock import Mock

from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.coordinator import CoordinatorOutput
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
        data={
            "name": "Test HAEO",
            "horizon_hours": 24,
            "period_minutes": 5,
            "optimizer": "highs",
        },
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)
    return entry


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

    coordinator.data = {
        "network": {
            OUTPUT_NAME_OPTIMIZATION_COST: CoordinatorOutput(
                type=OUTPUT_TYPE_COST,
                unit="$",
                state=12.5,
                forecast=None,
            ),
        },
        "battery": {
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
        f"{config_entry.entry_id}_network_{OUTPUT_NAME_OPTIMIZATION_COST}",
        f"{config_entry.entry_id}_battery_{OUTPUT_NAME_POWER_CONSUMED}",
    }

    names = {sensor.name for sensor in sensors}
    assert names == {"Network Optimization Cost", "Battery Power Consumed"}


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

    coordinator.data = {
        "battery": {},  # Empty outputs
        "network": {
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
    assert sensors[0].unique_id == f"{config_entry.entry_id}_network_{OUTPUT_NAME_OPTIMIZATION_COST}"


def test_sensor_native_value_returns_first_value(coordinator: Mock) -> None:
    """The first value in the output series becomes the sensor reading."""

    output_data = CoordinatorOutput(OUTPUT_TYPE_POWER, "kW", 3.5, forecast=None)
    coordinator.data = {"battery": {OUTPUT_NAME_POWER_CONSUMED: output_data}}

    sensor = HaeoSensor(
        coordinator,
        element_name="battery",
        output_name=OUTPUT_NAME_POWER_CONSUMED,
        output_data=output_data,
        unique_id="unique-id",
    )
    sensor.async_write_ha_state = Mock()

    sensor._handle_coordinator_update()

    assert sensor.native_value == 3.5


def test_sensor_native_value_handles_missing_data(coordinator: Mock) -> None:
    """Sensors return None when the coordinator has no data for them."""

    output_data = CoordinatorOutput(OUTPUT_TYPE_POWER, "kW", 3.5, forecast=None)
    coordinator.data = {}

    sensor = HaeoSensor(
        coordinator,
        element_name="battery",
        output_name=OUTPUT_NAME_POWER_CONSUMED,
        output_data=output_data,
        unique_id="unique-id",
    )
    sensor.async_write_ha_state = Mock()

    sensor._handle_coordinator_update()

    assert sensor.native_value is None


def test_extra_state_attributes_include_forecast(coordinator: Mock) -> None:
    """Forecast values beyond the first datapoint are exposed."""

    base_timestamp = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp())
    forecast = {
        datetime.fromtimestamp(base_timestamp, tz=UTC).isoformat(): 10.0,
        datetime.fromtimestamp(base_timestamp + 3600, tz=UTC).isoformat(): 11.0,
        datetime.fromtimestamp(base_timestamp + 7200, tz=UTC).isoformat(): 12.0,
    }
    output_data = CoordinatorOutput(OUTPUT_TYPE_COST, "USD", 10.0, forecast=forecast)
    coordinator.data = {"network": {OUTPUT_NAME_OPTIMIZATION_COST: output_data}}

    sensor = HaeoSensor(
        coordinator,
        element_name="network",
        output_name=OUTPUT_NAME_OPTIMIZATION_COST,
        output_data=output_data,
        unique_id="cost-id",
    )
    sensor.async_write_ha_state = Mock()

    sensor._handle_coordinator_update()

    attrs = sensor.extra_state_attributes
    assert attrs == {"forecast": forecast}


def test_extra_state_attributes_empty_when_no_data(coordinator: Mock) -> None:
    """Sensors expose no extra attributes when coordinator has no data."""

    output_data = CoordinatorOutput(OUTPUT_TYPE_POWER, "kW", 1.0, forecast=None)
    coordinator.data = {}

    sensor = HaeoSensor(
        coordinator,
        element_name="battery",
        output_name=OUTPUT_NAME_POWER_CONSUMED,
        output_data=output_data,
        unique_id="power-id",
    )
    sensor.async_write_ha_state = Mock()

    sensor._handle_coordinator_update()

    assert sensor.extra_state_attributes == {}


def test_sensor_availability_tracks_coordinator_status(coordinator: Mock) -> None:
    """Availability mirrors the coordinator's last update success flag."""

    output_data = CoordinatorOutput(OUTPUT_TYPE_COST, "USD", 5.0, forecast=None)
    coordinator.data = {"network": {OUTPUT_NAME_OPTIMIZATION_COST: output_data}}

    sensor = HaeoSensor(
        coordinator,
        element_name="network",
        output_name=OUTPUT_NAME_OPTIMIZATION_COST,
        output_data=output_data,
        unique_id="availability-id",
    )

    coordinator.last_update_success = True
    assert sensor.available is True

    coordinator.last_update_success = False
    assert sensor.available is False


def test_sensor_handles_forecast_timestamps(coordinator: Mock) -> None:
    """Coordinator timestamps do not affect sensor readings."""

    coordinator.last_optimization_time = datetime.now(tz=UTC)
    output_data = CoordinatorOutput(OUTPUT_TYPE_COST, "USD", 6.0, forecast=None)
    coordinator.data = {"network": {OUTPUT_NAME_OPTIMIZATION_COST: output_data}}

    sensor = HaeoSensor(
        coordinator,
        element_name="network",
        output_name=OUTPUT_NAME_OPTIMIZATION_COST,
        output_data=output_data,
        unique_id="timestamp-id",
    )
    sensor.async_write_ha_state = Mock()

    sensor._handle_coordinator_update()

    assert sensor.native_value == 6.0
