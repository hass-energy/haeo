"""Tests for deferred output sensor creation on the HAEO sensor platform.

When the first optimisation after a (re)load fails, ``coordinator.data`` is still
``None`` while the sensor platform is set up. The platform must add the output
sensors once the coordinator first produces data, rather than leaving the entry
with only the horizon sensor until it is reloaded.
"""

from datetime import UTC, datetime
from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import DOMAIN, ELEMENT_TYPE_NETWORK, OUTPUT_NAME_OPTIMIZATION_COST
from custom_components.haeo.coordinator.coordinator import (
    CoordinatorData,
    CoordinatorOutput,
    HaeoDataUpdateCoordinator,
    SubentryDevices,
)
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.model.output_data import OutputType
from custom_components.haeo.entities.haeo_horizon import HaeoHorizonEntity
from custom_components.haeo.flows import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON, HUB_SECTION_TIERS
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.sensor import _build_output_entities, async_setup_entry

NETWORK_TITLE = "Test Network"


@pytest.fixture
def horizon_manager() -> Mock:
    """Return a mock horizon manager."""
    manager = Mock(spec=HorizonManager)
    manager.get_forecast_timestamps.return_value = (0.0, 300.0, 600.0)
    manager.subscribe.return_value = Mock()
    return manager


@pytest.fixture
def coordinator() -> Mock:
    """Return a mock coordinator with no data and a recording listener registry."""
    mock = Mock(spec=HaeoDataUpdateCoordinator)
    mock.data = None
    mock.last_update_success = False
    mock.listeners = []

    def _add_listener(update_callback: object, context: object = None) -> object:
        mock.listeners.append(update_callback)

        def _remove() -> None:
            if update_callback in mock.listeners:
                mock.listeners.remove(update_callback)

        return _remove

    mock.async_add_listener.side_effect = _add_listener
    return mock


@pytest.fixture
def config_entry(hass: HomeAssistant, horizon_manager: Mock, coordinator: Mock) -> MockConfigEntry:
    """Return a hub config entry whose first optimisation has not produced data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Network",
        data={
            HUB_SECTION_COMMON: {CONF_NAME: "Test Network"},
            HUB_SECTION_TIERS: {
                "tier_1_count": 2,
                "tier_1_duration": 5,
                "tier_2_count": 0,
                "tier_2_duration": 15,
                "tier_3_count": 0,
                "tier_3_duration": 30,
                "tier_4_count": 0,
                "tier_4_duration": 60,
            },
            HUB_SECTION_ADVANCED: {},
        },
        entry_id="test_sensor_deferred_entry",
    )
    entry.add_to_hass(hass)
    coordinator.config_entry = entry
    entry.runtime_data = HaeoRuntimeData(coordinator=coordinator, horizon_manager=horizon_manager)
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data=MappingProxyType({CONF_ELEMENT_TYPE: ELEMENT_TYPE_NETWORK, CONF_NAME: NETWORK_TITLE}),
            subentry_type=ELEMENT_TYPE_NETWORK,
            title=NETWORK_TITLE,
            unique_id=None,
        ),
    )
    return entry


async def _setup_platform(hass: HomeAssistant, entry: MockConfigEntry) -> list[list[SensorEntity]]:
    """Run the sensor platform setup, returning each async_add_entities batch."""
    batches: list[list[SensorEntity]] = []

    def _add_entities(new_entities: object, update_before_add: bool = False) -> None:  # noqa: FBT002
        batches.append(list(new_entities))  # type: ignore[call-overload]

    await async_setup_entry(hass, entry, _add_entities)  # type: ignore[arg-type]
    await hass.async_block_till_done()
    return batches


def _coordinator_data() -> CoordinatorData:
    """Return coordinator data carrying a single network output."""
    now = datetime.now(UTC)
    outputs: dict[str, SubentryDevices] = {
        NETWORK_TITLE: {
            "network": {
                OUTPUT_NAME_OPTIMIZATION_COST: CoordinatorOutput(
                    type=OutputType.COST, unit="$", state=1.23, forecast=None
                ),
            }
        }
    }
    return CoordinatorData(context=Mock(), outputs=outputs, started_at=now, completed_at=now)


async def test_horizon_sensor_added_when_data_is_none(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """The horizon sensor is still created when the first optimisation failed."""
    batches = await _setup_platform(hass, config_entry)

    assert [type(entity).__name__ for entity in batches[0]] == [HaeoHorizonEntity.__name__]


async def test_listener_registered_when_data_is_none(
    hass: HomeAssistant, config_entry: MockConfigEntry, coordinator: Mock
) -> None:
    """A coordinator listener is registered so the outputs can be backfilled."""
    await _setup_platform(hass, config_entry)

    assert len(coordinator.listeners) == 1


async def test_outputs_added_on_first_successful_update(
    hass: HomeAssistant, config_entry: MockConfigEntry, coordinator: Mock
) -> None:
    """The first successful update creates the deferred output sensors."""
    batches = await _setup_platform(hass, config_entry)
    assert len(batches) == 1

    coordinator.data = _coordinator_data()
    coordinator.last_update_success = True
    for listener in list(coordinator.listeners):
        listener()
    await hass.async_block_till_done()

    assert len(batches) == 2, "expected a second async_add_entities call after recovery"
    assert [type(entity).__name__ for entity in batches[1]] == ["HaeoSensor"]


async def test_listener_removed_after_backfill(
    hass: HomeAssistant, config_entry: MockConfigEntry, coordinator: Mock
) -> None:
    """The listener removes itself so later updates do not duplicate entities."""
    batches = await _setup_platform(hass, config_entry)

    coordinator.data = _coordinator_data()
    for listener in list(coordinator.listeners):
        listener()
    await hass.async_block_till_done()

    assert coordinator.listeners == []
    assert len(batches) == 2

    # A further update must not add anything else.
    for listener in list(coordinator.listeners):
        listener()
    await hass.async_block_till_done()

    assert len(batches) == 2


async def test_failed_update_does_not_add_outputs(
    hass: HomeAssistant, config_entry: MockConfigEntry, coordinator: Mock
) -> None:
    """An update that leaves data as None keeps the listener registered."""
    batches = await _setup_platform(hass, config_entry)

    for listener in list(coordinator.listeners):
        listener()
    await hass.async_block_till_done()

    assert len(batches) == 1
    assert len(coordinator.listeners) == 1, "listener must stay until a successful update"


async def test_no_listener_registered_when_data_present(
    hass: HomeAssistant, config_entry: MockConfigEntry, coordinator: Mock
) -> None:
    """The deferred path is skipped entirely when the first optimisation succeeded."""
    coordinator.data = _coordinator_data()
    coordinator.last_update_success = True

    batches = await _setup_platform(hass, config_entry)

    assert len(batches) == 1
    assert coordinator.listeners == []


async def test_listener_removed_on_unload(
    hass: HomeAssistant, config_entry: MockConfigEntry, coordinator: Mock
) -> None:
    """Unloading before any successful update deregisters the listener.

    The platform is driven directly rather than through ``hass.config_entries``,
    so the entry never reaches ``LOADED`` and ``async_unload`` short-circuits
    without running the unload callbacks. Process them explicitly instead, as
    ``test_init`` notes for the same reason.
    """
    await _setup_platform(hass, config_entry)
    assert len(coordinator.listeners) == 1

    await config_entry._async_process_on_unload(hass)
    await hass.async_block_till_done()

    assert coordinator.listeners == []


async def test_build_output_entities_without_data(
    hass: HomeAssistant, config_entry: MockConfigEntry, coordinator: Mock
) -> None:
    """The builder is defensive if called before the coordinator has data."""
    assert _build_output_entities(hass, config_entry, coordinator) == []
