"""Tests for holding a source's last reading through a gap, and planning degraded once the hold passes."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from unittest.mock import AsyncMock, Mock, patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.const import CONF_INTEGRATION_TYPE, DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.core.const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON,
    CONF_INPUT_HOLD_SECONDS,
    CONF_NAME,
    DEFAULT_DEBOUNCE_SECONDS,
    HORIZON_PRESET_2_DAYS,
    HUB_SECTION_ADVANCED,
    HUB_SECTION_COMMON,
)
from custom_components.haeo.core.data.input_store import InputStore, create_input_store
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.grid import CONF_PRICE_SOURCE_TARGET, CONF_PRICE_TARGET_SOURCE
from custom_components.haeo.core.schema.field_hints import FieldHint
from custom_components.haeo.core.schema.horizon_value import as_horizon_preset_value
from custom_components.haeo.core.schema.sections import SECTION_POWER_LIMITS, SECTION_PRICING
from custom_components.haeo.entities.input_attributes import ATTR_HELD_SINCE, ATTR_HELD_SOURCE_ENTITY
from custom_components.haeo.inputs.hold_expiry import InputHoldExpiry
from custom_components.haeo.inputs.source_loader import SourceInputLoader
from custom_components.haeo.migrations import MIGRATION_MINOR_VERSION

PRICE_SENSOR = "sensor.import_price"
# Starts well clear of a minute boundary, so a held reading expires before the horizon moves
START = datetime(2025, 1, 1, 12, 0, 5, tzinfo=UTC)
HOLD_SECONDS = 30


class _NoStorage:
    async def write(self, value: object) -> None:
        """Discard the value; these stores are never edited."""


def _store(hold_seconds: float) -> InputStore:
    return create_input_store(
        value=as_entity_value([PRICE_SENSOR]),
        storage=_NoStorage(),
        hint=FieldHint(output_type=OutputType.PRICE),
        get_forecast_timestamps=lambda: (0.0, 60.0),
        hold_seconds=hold_seconds,
    )


def _price(state: str) -> FakeStateMachine:
    return FakeStateMachine({PRICE_SENSOR: FakeEntityState(PRICE_SENSOR, state, {})})


async def test_hold_expiry_degrades_each_store_when_its_held_reading_is_too_old(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Each store holding a reading is marked degraded and notified when its hold passes, with no reload."""
    freezer.move_to(START)
    short, long = _store(10), _store(20)
    expiry = InputHoldExpiry(hass, {("Short", ("price",)): short, ("Long", ("price",)): long})
    expiry.start()
    notified: list[str] = []
    short.add_listener(lambda: notified.append("short"))
    long.add_listener(lambda: notified.append("long"))
    for store in (long, short):
        store.load(_price("0.3"))
        store.load(_price("unavailable"))
        store.notify_listeners()
    notified.clear()

    freezer.tick(10)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert notified == ["short"]
    assert short.available
    assert short.degraded_sources == (PRICE_SENSOR,)
    assert long.degraded_sources == ()

    freezer.tick(10)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert notified == ["short", "long"]
    assert long.available
    assert long.degraded_sources == (PRICE_SENSOR,)

    expiry.cleanup()


async def test_hold_expiry_ignores_a_hold_that_ended(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """A store whose source reads again before its hold passes is not degraded when the hold would have expired."""
    freezer.move_to(START)
    store = _store(10)
    expiry = InputHoldExpiry(hass, {("Grid", ("price",)): store})
    expiry.start()
    store.load(_price("0.3"))
    store.load(_price("unavailable"))
    store.notify_listeners()
    store.load(_price("0.4"))
    store.notify_listeners()

    freezer.tick(10)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert store.degraded_sources == ()
    expiry.cleanup()


@pytest.fixture
async def hub(hass: HomeAssistant, freezer: FrozenDateTimeFactory, hold_seconds: int) -> MockConfigEntry:
    """Set up a hub whose grid reads its import price from a sensor, and run its first optimization."""
    freezer.move_to(START)
    hass.states.async_set(PRICE_SENSOR, "0.3")
    entry = await _setup_hub(hass, hold_seconds)
    assert _status(entry) == "success"
    return entry


async def _setup_hub(hass: HomeAssistant, hold_seconds: int) -> MockConfigEntry:
    """Set up a hub whose grid reads its import price from the price sensor."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            HUB_SECTION_COMMON: {CONF_NAME: "Home", CONF_HORIZON: as_horizon_preset_value(HORIZON_PRESET_2_DAYS)},
            HUB_SECTION_ADVANCED: {
                CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS,
                CONF_INPUT_HOLD_SECONDS: hold_seconds,
            },
        },
        minor_version=MIGRATION_MINOR_VERSION,
    )
    entry.add_to_hass(hass)
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data=MappingProxyType(
                {
                    CONF_ELEMENT_TYPE: ElementType.GRID,
                    CONF_NAME: "Grid",
                    "connection": as_connection_target("Switchboard"),
                    SECTION_PRICING: {
                        CONF_PRICE_SOURCE_TARGET: as_entity_value([PRICE_SENSOR]),
                        CONF_PRICE_TARGET_SOURCE: as_constant_value(0.1),
                    },
                    SECTION_POWER_LIMITS: {},
                }
            ),
            subentry_type=ElementType.GRID,
            title="Grid",
            unique_id=None,
        ),
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _coordinator(entry: MockConfigEntry) -> HaeoDataUpdateCoordinator:
    runtime_data = entry.runtime_data
    assert runtime_data is not None
    assert runtime_data.coordinator is not None
    return runtime_data.coordinator


def _status(entry: MockConfigEntry) -> str:
    return _coordinator(entry).optimization_status


def _price_entity_id(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    grid = next(subentry for subentry in entry.subentries.values() if subentry.title == "Grid")
    entity_id = er.async_get(hass).async_get_entity_id(
        "number", DOMAIN, f"{entry.entry_id}_{grid.subentry_id}_{CONF_PRICE_SOURCE_TARGET}"
    )
    assert entity_id is not None
    return entity_id


def _issue(hass: HomeAssistant, entry: MockConfigEntry, kind: str) -> ir.IssueEntry | None:
    field = f"{SECTION_PRICING}.{CONF_PRICE_SOURCE_TARGET}"
    return ir.async_get(hass).async_get_issue(DOMAIN, f"{kind}_input_{entry.entry_id}_Grid_{field}")


async def _wait(hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float) -> None:
    """Let time pass, running every timer due in it."""
    freezer.tick(seconds)
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()


async def _set_price(hass: HomeAssistant, freezer: FrozenDateTimeFactory, state: str) -> None:
    """Set the price sensor, then let the optimization it requests run."""
    hass.states.async_set(PRICE_SENSOR, state)
    await hass.async_block_till_done()
    await _wait(hass, freezer, timedelta(seconds=DEFAULT_DEBOUNCE_SECONDS + 1).total_seconds())


@pytest.mark.parametrize("hold_seconds", [HOLD_SECONDS])
async def test_short_gap_keeps_optimizing_on_the_held_reading(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, hub: MockConfigEntry
) -> None:
    """A sensor gap shorter than the hold keeps the input available and optimizing, and names the held sensor."""
    price_entity = _price_entity_id(hass, hub)
    lost_at = dt_util.utcnow()
    plan = _coordinator(hub).data

    await _set_price(hass, freezer, "unavailable")

    assert _status(hub) == "success"
    # The held reading is the value already planned on, so the gap does not re-optimize
    assert _coordinator(hub).data is plan
    state = hass.states.get(price_entity)
    assert state is not None
    assert state.state == "0.3"
    assert state.attributes[ATTR_HELD_SOURCE_ENTITY] == PRICE_SENSOR
    assert state.attributes[ATTR_HELD_SINCE] == lost_at
    assert _issue(hass, hub, "degraded") is None

    await _set_price(hass, freezer, "0.4")

    assert _status(hub) == "success"
    assert _coordinator(hub).data is not plan
    state = hass.states.get(price_entity)
    assert state is not None
    assert state.state == "0.4"
    assert ATTR_HELD_SOURCE_ENTITY not in state.attributes
    assert ATTR_HELD_SINCE not in state.attributes


@pytest.mark.parametrize("hold_seconds", [HOLD_SECONDS])
async def test_long_gap_keeps_optimizing_degraded_until_the_sensor_reports(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, hub: MockConfigEntry
) -> None:
    """Once the hold passes HAEO keeps optimizing on the last reading, reports degraded, and raises an issue."""
    price_entity = _price_entity_id(hass, hub)
    lost_at = dt_util.utcnow()
    await _set_price(hass, freezer, "unavailable")
    assert _status(hub) == "success"
    plan = _coordinator(hub).data

    await _wait(hass, freezer, HOLD_SECONDS)
    await _wait(hass, freezer, DEFAULT_DEBOUNCE_SECONDS + 1)

    assert _status(hub) == "degraded"
    assert _coordinator(hub).data is not plan
    state = hass.states.get(price_entity)
    assert state is not None
    assert state.state == "0.3"
    assert state.attributes[ATTR_HELD_SINCE] == lost_at
    assert _issue(hass, hub, "unavailable") is None
    issue = _issue(hass, hub, "degraded")
    assert issue is not None
    assert issue.translation_placeholders == {
        "element": "Grid",
        "field": f"{SECTION_PRICING}.{CONF_PRICE_SOURCE_TARGET}",
        "entities": PRICE_SENSOR,
        "since": dt_util.as_local(lost_at).strftime("%Y-%m-%d %H:%M:%S"),
    }

    # The sensor reporting its old reading again leaves the value as it is, but still ends the degradation
    await _set_price(hass, freezer, "0.3")

    assert _status(hub) == "success"
    assert _issue(hass, hub, "degraded") is None


@pytest.mark.parametrize("hold_seconds", [0])
async def test_no_hold_reports_degraded_as_soon_as_a_sensor_has_no_reading(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, hub: MockConfigEntry
) -> None:
    """With no hold, a sensor without a reading degrades the plan at once rather than stopping it."""
    await _set_price(hass, freezer, "unavailable")

    assert _status(hub) == "degraded"
    assert _issue(hass, hub, "degraded") is not None
    assert _issue(hass, hub, "unavailable") is None


def _recorder(state: State | None) -> Mock:
    """Return a recorder instance whose executor jobs return the given recorded state."""

    async def run(_func: Callable[..., object], *_args: object) -> object:
        return state

    recorder = Mock()
    recorder.async_add_executor_job = AsyncMock(side_effect=run)
    return recorder


@pytest.mark.parametrize(
    ("age", "status"),
    [pytest.param(HOLD_SECONDS * 4, "degraded", id="older_than_the_hold"), pytest.param(10, "success", id="within")],
)
async def test_sensor_unavailable_at_startup_plans_on_its_recorded_reading(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, age: int, status: str
) -> None:
    """A sensor without a reading at startup is held from its last recorded report, so the hold counts from then."""
    freezer.move_to(START)
    hass.config.components.add("recorder")
    hass.states.async_set(PRICE_SENSOR, "unavailable")
    reported_at = dt_util.utcnow() - timedelta(seconds=age)
    # The reading last changed long ago, but was last reported only shortly before the restart
    changed_at = reported_at - timedelta(hours=1)
    recorded = State(PRICE_SENSOR, "0.3", last_changed=changed_at, last_updated=changed_at, last_reported=reported_at)
    recorder = _recorder(recorded)

    with patch("custom_components.haeo.inputs.recorded_reading.get_instance", return_value=recorder):
        hub = await _setup_hub(hass, HOLD_SECONDS)

        assert _status(hub) == status
        state = hass.states.get(_price_entity_id(hass, hub))
        assert state is not None
        assert state.state == "0.3"
        assert state.attributes[ATTR_HELD_SOURCE_ENTITY] == PRICE_SENSOR
        assert state.attributes[ATTR_HELD_SINCE] == reported_at
        assert (_issue(hass, hub, "degraded") is not None) is (status == "degraded")

        await _wait(hass, freezer, HOLD_SECONDS - age + 1)
        await _set_price(hass, freezer, "unknown")

    assert _status(hub) == "degraded"
    issue = _issue(hass, hub, "degraded")
    assert issue is not None
    assert issue.translation_placeholders is not None
    assert issue.translation_placeholders["since"] == dt_util.as_local(reported_at).strftime("%Y-%m-%d %H:%M:%S")
    # The recorder is asked once, however often the store reloads
    assert recorder.async_add_executor_job.await_count == 1


async def test_sensor_without_a_recorded_reading_leaves_its_input_unavailable(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A sensor with no recorded reading has nothing to plan with, so its input stays unavailable."""
    freezer.move_to(START)
    hass.config.components.add("recorder")
    hass.states.async_set(PRICE_SENSOR, "unavailable")
    store = _store(HOLD_SECONDS)
    horizon_manager = Mock()
    horizon_manager.subscribe.return_value = lambda: None
    recorder = _recorder(None)
    loader = SourceInputLoader(hass, {("Grid", ("price",)): store}, horizon_manager)

    with patch("custom_components.haeo.inputs.recorded_reading.get_instance", return_value=recorder):
        loader.start()
        await hass.async_block_till_done()
        hass.states.async_set(PRICE_SENSOR, "unknown")
        await hass.async_block_till_done()

    assert not store.available
    assert store.unavailable_sources == (PRICE_SENSOR,)
    assert recorder.async_add_executor_job.await_count == 1
    loader.cleanup()
