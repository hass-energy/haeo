"""Tests for keeping the recent history of an input's source entities."""

from collections.abc import Mapping
from datetime import timedelta
from unittest.mock import ANY, patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.recorder.core import Recorder
from homeassistant.core import HomeAssistant, State
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.components.recorder.common import async_wait_recording_done

from custom_components.haeo.core.data.loader.source_history import OFF_PERIODS_ATTRIBUTE, READINGS_ATTRIBUTE
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.ha_state_machine import HomeAssistantStateMachine
from custom_components.haeo.source_history import LOOKBACK, HistoryStateMachine, SourceHistory

PLUG = "binary_sensor.ev_plug"
ODOMETER = "sensor.ev_odometer"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock: Recorder, enable_custom_integrations: None) -> Recorder:
    """Start the recorder before hass, then enable custom integrations as usual."""
    return recorder_mock


def _off_periods(history: SourceHistory, entity_id: str = PLUG) -> object:
    return history.attributes()[entity_id][OFF_PERIODS_ATTRIBUTE]


async def test_load_reads_recorded_off_periods(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Loading reads the plug's recorded unplugged periods."""
    hass.states.async_set(PLUG, "on")
    freezer.tick(timedelta(minutes=10))
    unplugged = dt_util.utcnow()
    hass.states.async_set(PLUG, "off")
    freezer.tick(timedelta(minutes=30))
    plugged_in = dt_util.utcnow()
    hass.states.async_set(PLUG, "on")
    await async_wait_recording_done(hass)

    history = SourceHistory(hass, [PLUG], OutputType.AVAILABILITY)
    await history.async_load()

    assert _off_periods(history) == [(pytest.approx(unplugged.timestamp()), pytest.approx(plugged_in.timestamp()))]


async def test_load_reads_recorded_readings(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """A distance source's history is its numeric readings."""
    hass.states.async_set(ODOMETER, "10000")
    freezer.tick(timedelta(minutes=10))
    hass.states.async_set(ODOMETER, "10012.5")
    await async_wait_recording_done(hass)

    history = SourceHistory(hass, [ODOMETER], OutputType.DISTANCE)
    await history.async_load()

    assert history.attributes()[ODOMETER] == {READINGS_ATTRIBUTE: [(ANY, 10000.0), (ANY, 10012.5)]}


async def test_record_appends_changes_without_querying(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """New source states extend the history without another recorder query."""
    hass.states.async_set(PLUG, "on")
    await async_wait_recording_done(hass)
    history = SourceHistory(hass, [PLUG], OutputType.AVAILABILITY)
    await history.async_load()

    with patch("custom_components.haeo.source_history.history.state_changes_during_period") as query:
        freezer.tick(timedelta(minutes=5))
        unplugged = dt_util.utcnow()
        hass.states.async_set(PLUG, "off")
        history.record(PLUG, hass.states.get(PLUG))
        history.record(PLUG, hass.states.get(PLUG))

    query.assert_not_called()
    assert _off_periods(history) == [(pytest.approx(unplugged.timestamp()), None)]


async def test_live_state_newer_than_recorded_is_included(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """A plug-in the recorder has not committed yet still ends the off period."""
    hass.states.async_set(PLUG, "off")
    await async_wait_recording_done(hass)
    unplugged = dt_util.utcnow()
    freezer.tick(timedelta(minutes=30))
    plugged_in = dt_util.utcnow()

    with patch("custom_components.haeo.source_history.history.state_changes_during_period") as changes:
        changes.side_effect = lambda *_args, **_kwargs: {PLUG: [State(PLUG, "off", last_changed=unplugged)]}
        hass.states.async_set(PLUG, "on")
        history = SourceHistory(hass, [PLUG], OutputType.AVAILABILITY)
        await history.async_load()

    assert _off_periods(history) == [(pytest.approx(unplugged.timestamp()), pytest.approx(plugged_in.timestamp()))]


async def test_changes_older_than_lookback_are_dropped(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """An unplug before the lookback is forgotten once a later change arrives."""
    hass.states.async_set(PLUG, "off")
    await async_wait_recording_done(hass)
    history = SourceHistory(hass, [PLUG], OutputType.AVAILABILITY)
    await history.async_load()
    freezer.tick(timedelta(minutes=1))
    hass.states.async_set(PLUG, "on")
    history.record(PLUG, hass.states.get(PLUG))

    freezer.tick(LOOKBACK + timedelta(hours=1))
    hass.states.async_set(PLUG, "off")
    history.record(PLUG, hass.states.get(PLUG))

    assert _off_periods(history) == [(pytest.approx(dt_util.utcnow().timestamp()), None)]


@pytest.mark.parametrize("failure", ["no_recorder", "query_fails"])
async def test_without_recorded_history_only_the_live_state_counts(hass: HomeAssistant, failure: str) -> None:
    """Without the recorder, or when the query fails, the history starts from the live state."""
    hass.states.async_set(PLUG, "off")
    history = SourceHistory(hass, [PLUG], OutputType.AVAILABILITY)
    if failure == "no_recorder":
        hass.config.components.remove("recorder")
        await history.async_load()
    else:
        with patch(
            "custom_components.haeo.source_history.history.state_changes_during_period",
            side_effect=RuntimeError("database locked"),
        ):
            await history.async_load()

    state = hass.states.get(PLUG)
    assert state is not None
    assert _off_periods(history) == [(pytest.approx(state.last_changed_timestamp), None)]


async def test_state_machine_injects_history(hass: HomeAssistant) -> None:
    """The wrapped state machine adds history attributes only where there are some."""
    hass.states.async_set(PLUG, "on")
    hass.states.async_set("binary_sensor.other", "on")
    periods = [(100.0, 200.0)]

    sm = HistoryStateMachine(HomeAssistantStateMachine(hass), {PLUG: {OFF_PERIODS_ATTRIBUTE: periods}})

    plug = sm.get(PLUG)
    assert plug is not None
    assert plug.state == "on"
    assert plug.attributes[OFF_PERIODS_ATTRIBUTE] == periods
    serialized_attributes = plug.as_dict()["attributes"]
    assert isinstance(serialized_attributes, Mapping)
    assert serialized_attributes[OFF_PERIODS_ATTRIBUTE] == periods
    other = sm.get("binary_sensor.other")
    assert other is not None
    assert OFF_PERIODS_ATTRIBUTE not in other.attributes
    assert sm.get("binary_sensor.missing") is None
