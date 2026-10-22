"""Tests for setting up the HAEO sensor platform."""

from collections.abc import Callable
from datetime import UTC, datetime
from types import MappingProxyType

# Coordinator output fixtures use runtime string keys that cannot satisfy the
# Literal key types of SubentryDevices.
from typing import Any  # noqa: TID251
from unittest.mock import Mock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntryState, ConfigSubentry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from conftest import added_entities
from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import (
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
    OUTPUT_NAME_OPTIMIZATION_COST,
    OUTPUT_NAME_OPTIMIZATION_DURATION,
)
from custom_components.haeo.coordinator import ForecastPoint
from custom_components.haeo.core.adapters.elements.load import LOAD_POWER
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_HORIZON, CONF_NAME, HORIZON_PRESET_2_DAYS
from custom_components.haeo.core.model import OutputType
from custom_components.haeo.core.model.elements.connection import CONNECTION_POWER
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.battery import ELEMENT_TYPE as BATTERY_TYPE
from custom_components.haeo.core.schema.elements.battery import SECTION_LIMITS
from custom_components.haeo.core.schema.horizon_value import as_horizon_preset_value
from custom_components.haeo.entities import HaeoSensor
from custom_components.haeo.entities.tests.sensor_helpers import (
    create_mock_coordinator,
    make_coordinator_data,
    make_output,
)
from custom_components.haeo.flows import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON
from custom_components.haeo.sensor import async_setup_entry


def _create_mock_horizon_manager() -> Mock:
    """Create a mock horizon manager for tests."""
    horizon = Mock()
    horizon.get_forecast_timestamps.return_value = (1000.0, 2000.0, 3000.0)
    horizon.period_count = 3
    horizon.smallest_period = 300
    horizon.subscribe.return_value = Mock()  # Unsubscribe callback
    return horizon


def _create_mock_runtime_data(coordinator: Mock) -> HaeoRuntimeData:
    """Create mock runtime data with horizon manager and coordinator."""
    horizon = _create_mock_horizon_manager()
    return HaeoRuntimeData(horizon_manager=horizon, coordinator=coordinator)


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a config entry configured for the sensor platform tests."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Mock Network",
        data={
            HUB_SECTION_COMMON: {
                CONF_NAME: "Mock Network",
                CONF_HORIZON: as_horizon_preset_value(HORIZON_PRESET_2_DAYS),
            },
            HUB_SECTION_ADVANCED: {},
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
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: BATTERY_TYPE,
                CONF_NAME: "Battery",
                "connection": "Switchboard",
                "capacity": 10.0,
                "initial_charge_percentage": 50.0,
                SECTION_LIMITS: {},
                "advanced": {},
            }
        ),
        subentry_type=BATTERY_TYPE,
        title="Battery",
        unique_id=None,
    )

    hass.config_entries.async_add_subentry(entry, network_subentry)
    hass.config_entries.async_add_subentry(entry, battery_subentry)

    return entry


async def test_async_setup_entry_creates_sensors_with_metadata(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Sensors inherit metadata supplied by coordinator outputs."""

    coordinator = create_mock_coordinator()
    network_key = config_entry.title
    battery_key = "Battery"

    coordinator.data = make_coordinator_data(
        {
            network_key: {
                network_key: {
                    OUTPUT_NAME_OPTIMIZATION_DURATION: make_output(
                        type_=OutputType.DURATION,
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
                    LOAD_POWER: make_output(
                        type_=OutputType.POWER,
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
    )
    config_entry.runtime_data = _create_mock_runtime_data(coordinator)

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    sensors = added_entities(async_add_entities)
    # Horizon and status sensors, then 2 output sensors
    assert [type(sensor).__name__ for sensor in sensors[:2]] == ["HaeoHorizonEntity", "HaeoStatusSensor"]
    assert len(sensors) == 4

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
    """Horizon entity is added even when coordinator data is empty.

    The horizon entity is essential for input entities to function,
    so it must be included regardless of optimization output availability.
    """
    coordinator = create_mock_coordinator()
    coordinator.data = make_coordinator_data({})
    config_entry.runtime_data = _create_mock_runtime_data(coordinator)

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    # The horizon and status sensors are always added
    entities = added_entities(async_add_entities)
    assert [type(entity).__name__ for entity in entities] == ["HaeoHorizonEntity", "HaeoStatusSensor"]


async def test_async_setup_entry_creates_sub_device_sensors(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Sensors are created for sub-devices (e.g. nested components)."""

    coordinator = create_mock_coordinator()
    battery_key = "Battery"
    sub_device_key = "Battery Sub"

    coordinator.data = make_coordinator_data(
        {
            battery_key: {
                sub_device_key: {
                    LOAD_POWER: make_output(
                        type_=OutputType.POWER,
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
    )
    config_entry.runtime_data = _create_mock_runtime_data(coordinator)

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    sensors = added_entities(async_add_entities)
    # Horizon and status sensors, plus 1 output sensor
    assert len(sensors) == 3

    # Find the output sensor
    output_sensors = [s for s in sensors if isinstance(s, HaeoSensor)]
    assert len(output_sensors) == 1

    sensor = output_sensors[0]
    # Check that the sensor uses the output name as translation key (consistent with all sensors)
    assert sensor.translation_key == LOAD_POWER
    # Check that it's associated with the correct sub-device
    assert sensor._device_key == sub_device_key


async def test_async_setup_entry_flattens_connection_endpoints_into_placeholders(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """The connection power sensor's translated name resolves from the nested endpoints section.

    Home Assistant raises on a missing placeholder, which drops the sensor when it is added.
    """
    connection_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ElementType.CONNECTION,
                CONF_NAME: "ACEV to EV1",
                "endpoints": {
                    "source": as_connection_target("ACEV Charger"),
                    "target": as_connection_target("EV1 Port"),
                },
                "efficiency": {"efficiency_source_target": {"type": "constant", "value": 100.0}},
            }
        ),
        subentry_type=ElementType.CONNECTION,
        title="ACEV to EV1",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(config_entry, connection_subentry)

    coordinator = create_mock_coordinator()
    coordinator.data = make_coordinator_data(
        {
            "ACEV to EV1": {
                ElementType.CONNECTION: {
                    CONNECTION_POWER: make_output(
                        type_=OutputType.POWER_FLOW,
                        unit="kW",
                        state=11.14,
                        forecast=None,
                        entity_category=None,
                        device_class=SensorDeviceClass.POWER,
                        state_class=SensorStateClass.MEASUREMENT,
                        options=None,
                    )
                },
            },
        }
    )
    config_entry.runtime_data = _create_mock_runtime_data(coordinator)

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    sensors = [s for s in added_entities(async_add_entities) if isinstance(s, HaeoSensor)]
    assert len(sensors) == 1
    translations = await async_get_translations(hass, "en", "entity", integrations=[DOMAIN])
    name = translations[f"component.{DOMAIN}.entity.sensor.{sensors[0].translation_key}.name"]
    assert name.format(**sensors[0].translation_placeholders) == "ACEV Charger to EV1 Port power"


def _coordinator_without_data() -> tuple[Mock, list[Callable[[], None]]]:
    """Return a coordinator whose first optimization failed, and its registered listeners."""
    coordinator = create_mock_coordinator()
    coordinator.data = None
    coordinator.last_update_success = False
    listeners: list[Callable[[], None]] = []

    def add_listener(update_callback: Callable[[], None]) -> Callable[[], None]:
        listeners.append(update_callback)
        return lambda: listeners.remove(update_callback)

    coordinator.async_add_listener = add_listener
    return coordinator, listeners


def _network_outputs(network_key: str) -> dict[str, Any]:
    return {
        network_key: {
            network_key: {
                OUTPUT_NAME_OPTIMIZATION_COST: make_output(
                    type_=OutputType.COST,
                    unit="$",
                    state=1.0,
                    forecast=None,
                    entity_category=None,
                    device_class=SensorDeviceClass.MONETARY,
                    state_class=None,
                    options=None,
                ),
            },
        },
    }


async def test_outputs_added_after_failed_first_optimization(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Without data at setup only the horizon and status sensors are added.

    Outputs follow once, on the first successful update.
    """
    coordinator, listeners = _coordinator_without_data()
    config_entry.runtime_data = _create_mock_runtime_data(coordinator)
    config_entry.mock_state(hass, ConfigEntryState.LOADED)
    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)
    assert [type(entity).__name__ for entity in added_entities(async_add_entities)] == [
        "HaeoHorizonEntity",
        "HaeoStatusSensor",
    ]

    # A failed update adds nothing
    for listener in list(listeners):
        listener()
    assert len(added_entities(async_add_entities)) == 2

    coordinator.data = make_coordinator_data(_network_outputs(config_entry.title))
    for _ in range(2):
        for listener in list(listeners):
            listener()

    _, _, *outputs = added_entities(async_add_entities)
    assert [sensor.translation_key for sensor in outputs] == [OUTPUT_NAME_OPTIMIZATION_COST]


async def test_outputs_not_added_while_entry_unloads(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """An update that finishes while the entry is unloading adds no entities, and unloading removes the listener."""
    coordinator, listeners = _coordinator_without_data()
    config_entry.runtime_data = _create_mock_runtime_data(coordinator)
    config_entry.mock_state(hass, ConfigEntryState.LOADED)
    async_add_entities = Mock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    config_entry.mock_state(hass, ConfigEntryState.UNLOAD_IN_PROGRESS)
    coordinator.data = make_coordinator_data(_network_outputs(config_entry.title))
    for listener in list(listeners):
        listener()
    assert async_add_entities.call_count == 1

    await config_entry._async_process_on_unload(hass)
    assert listeners == []


async def test_status_sensor_keeps_previous_unique_id(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """The status sensor keeps the unique ID it had as a network output, so its entity ID is unchanged."""
    config_entry.runtime_data = _create_mock_runtime_data(create_mock_coordinator())
    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    network = next(s for s in config_entry.subentries.values() if s.subentry_type == ELEMENT_TYPE_NETWORK)
    status_sensor = async_add_entities.call_args.args[0][1]
    assert status_sensor.unique_id == (
        f"{config_entry.entry_id}_{network.subentry_id}_network_network_optimization_status"
    )
