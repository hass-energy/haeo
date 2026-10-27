"""Tests for holding a source's last reading through a short gap, and expiring it."""

from datetime import UTC, datetime, timedelta
from types import MappingProxyType

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.const import CONF_INTEGRATION_TYPE, DOMAIN, INTEGRATION_TYPE_HUB
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


async def test_hold_expiry_expires_each_store_when_its_held_reading_is_too_old(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Each store holding a reading is marked unavailable and notified when its hold passes, with no reload."""
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
    assert not short.available
    assert long.available

    freezer.tick(10)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert notified == ["short", "long"]
    assert not long.available

    expiry.cleanup()


async def test_hold_expiry_ignores_a_hold_that_ended(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """A store whose source reads again before its hold passes stays available when the hold would have expired."""
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

    assert store.available
    expiry.cleanup()


@pytest.fixture
async def hub(hass: HomeAssistant, freezer: FrozenDateTimeFactory, hold_seconds: int) -> MockConfigEntry:
    """Set up a hub whose grid reads its import price from a sensor, and run its first optimization."""
    freezer.move_to(START)
    hass.states.async_set(PRICE_SENSOR, "0.3")
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
    assert _status(entry) == "success"
    return entry


def _status(entry: MockConfigEntry) -> str:
    runtime_data = entry.runtime_data
    assert runtime_data is not None
    assert runtime_data.coordinator is not None
    return runtime_data.coordinator.optimization_status


def _price_entity_id(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    grid = next(subentry for subentry in entry.subentries.values() if subentry.title == "Grid")
    entity_id = er.async_get(hass).async_get_entity_id(
        "number", DOMAIN, f"{entry.entry_id}_{grid.subentry_id}_{CONF_PRICE_SOURCE_TARGET}"
    )
    assert entity_id is not None
    return entity_id


def _issue(hass: HomeAssistant, entry: MockConfigEntry) -> ir.IssueEntry | None:
    field = f"{SECTION_PRICING}.{CONF_PRICE_SOURCE_TARGET}"
    return ir.async_get(hass).async_get_issue(DOMAIN, f"unavailable_input_{entry.entry_id}_Grid_{field}")


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

    await _set_price(hass, freezer, "unavailable")

    assert _status(hub) == "success"
    state = hass.states.get(price_entity)
    assert state is not None
    assert state.state == "0.3"
    assert state.attributes[ATTR_HELD_SOURCE_ENTITY] == PRICE_SENSOR
    assert state.attributes[ATTR_HELD_SINCE] == lost_at
    assert _issue(hass, hub) is None

    await _set_price(hass, freezer, "0.4")

    assert _status(hub) == "success"
    state = hass.states.get(price_entity)
    assert state is not None
    assert state.state == "0.4"
    assert ATTR_HELD_SOURCE_ENTITY not in state.attributes
    assert ATTR_HELD_SINCE not in state.attributes


@pytest.mark.parametrize("hold_seconds", [HOLD_SECONDS])
async def test_long_gap_makes_the_input_unavailable_with_no_other_change(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, hub: MockConfigEntry
) -> None:
    """Once the hold passes the input becomes unavailable and raises its repair issue, and recovers with the sensor."""
    price_entity = _price_entity_id(hass, hub)
    await _set_price(hass, freezer, "unavailable")
    assert _status(hub) == "success"

    await _wait(hass, freezer, HOLD_SECONDS)
    await _wait(hass, freezer, DEFAULT_DEBOUNCE_SECONDS + 1)

    assert _status(hub) == "failed"
    state = hass.states.get(price_entity)
    assert state is not None
    assert state.state == "unavailable"
    issue = _issue(hass, hub)
    assert issue is not None
    assert issue.translation_placeholders is not None
    assert issue.translation_placeholders["entities"] == PRICE_SENSOR

    await _set_price(hass, freezer, "0.4")

    assert _status(hub) == "success"
    state = hass.states.get(price_entity)
    assert state is not None
    assert state.state == "0.4"
    assert _issue(hass, hub) is None


@pytest.mark.parametrize("hold_seconds", [0])
async def test_no_hold_stops_optimizing_as_soon_as_a_sensor_has_no_reading(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, hub: MockConfigEntry
) -> None:
    """With no hold, a sensor without a reading makes its input unavailable at once."""
    await _set_price(hass, freezer, "unavailable")

    assert _status(hub) == "failed"
    assert _issue(hass, hub) is not None
