"""Tests for looking up availability last off times from the recorder."""

from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.recorder.core import Recorder
from homeassistant.core import HomeAssistant, State
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.components.recorder.common import async_wait_recording_done

from custom_components.haeo.core.data.loader.last_off import LAST_OFF_ATTRIBUTE
from custom_components.haeo.ha_state_machine import HomeAssistantStateMachine
from custom_components.haeo.last_off_history import LOOKBACK, async_last_off, async_last_off_state_machine

PLUG = "binary_sensor.ev_plug"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock: Recorder, enable_custom_integrations: None) -> Recorder:
    """Start the recorder before hass, then enable custom integrations as usual."""
    return recorder_mock


async def test_last_off_reads_end_of_latest_off_reading(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """The last off time is when the plug last went from off to another state."""
    hass.states.async_set(PLUG, "off")
    freezer.tick(timedelta(minutes=30))
    plugged_in = dt_util.utcnow()
    hass.states.async_set(PLUG, "on")
    await async_wait_recording_done(hass)

    assert await async_last_off(hass, PLUG) == pytest.approx(plugged_in.timestamp())


async def test_restart_while_plugged_in_has_no_last_off(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """An unavailable reading between two plugged-in readings is not an unplug."""
    hass.states.async_set(PLUG, "on")
    freezer.tick(timedelta(minutes=30))
    hass.states.async_set(PLUG, "unavailable")
    freezer.tick(timedelta(minutes=1))
    hass.states.async_set(PLUG, "on")
    await async_wait_recording_done(hass)

    assert await async_last_off(hass, PLUG) is None


async def test_live_state_ends_off_reading_not_yet_recorded(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A plug-in the recorder has not committed yet still ends the off reading."""
    hass.states.async_set(PLUG, "off")
    await async_wait_recording_done(hass)
    freezer.tick(timedelta(minutes=30))
    plugged_in = dt_util.utcnow()

    with patch("custom_components.haeo.last_off_history.history.state_changes_during_period") as changes:
        changes.side_effect = lambda *_args, **_kwargs: {
            PLUG: [State(PLUG, "off", last_changed=plugged_in - timedelta(minutes=30))]
        }
        hass.states.async_set(PLUG, "on")
        assert await async_last_off(hass, PLUG) == pytest.approx(plugged_in.timestamp())


async def test_off_reading_older_than_lookback_is_ignored(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """An unplug before the lookback window loads as no last off time."""
    hass.states.async_set(PLUG, "off")
    freezer.tick(timedelta(minutes=1))
    hass.states.async_set(PLUG, "on")
    await async_wait_recording_done(hass)
    freezer.tick(LOOKBACK + timedelta(hours=1))

    assert await async_last_off(hass, PLUG) is None


async def test_without_recorder_has_no_last_off(hass: HomeAssistant) -> None:
    """Without the recorder loaded nothing is looked up."""
    hass.states.async_set(PLUG, "on")
    hass.config.components.remove("recorder")

    assert await async_last_off(hass, PLUG) is None


async def test_failed_query_has_no_last_off(hass: HomeAssistant) -> None:
    """A failing history query loads as no last off time."""
    hass.states.async_set(PLUG, "on")
    with patch(
        "custom_components.haeo.last_off_history.history.state_changes_during_period",
        side_effect=RuntimeError("database locked"),
    ):
        assert await async_last_off(hass, PLUG) is None


async def test_state_machine_injects_last_off(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """The wrapped state machine adds the last off attribute only where one was found."""
    hass.states.async_set(PLUG, "off")
    freezer.tick(timedelta(minutes=30))
    plugged_in = dt_util.utcnow()
    hass.states.async_set(PLUG, "on")
    hass.states.async_set("binary_sensor.other", "on")
    await async_wait_recording_done(hass)

    sm = await async_last_off_state_machine(
        hass, HomeAssistantStateMachine(hass), [PLUG, "binary_sensor.other", "binary_sensor.missing"]
    )

    plug = sm.get(PLUG)
    assert plug is not None
    assert plug.state == "on"
    assert plug.attributes[LAST_OFF_ATTRIBUTE] == pytest.approx(plugged_in.timestamp())
    assert plug.as_dict()["attributes"][LAST_OFF_ATTRIBUTE] == pytest.approx(plugged_in.timestamp())
    other = sm.get("binary_sensor.other")
    assert other is not None
    assert LAST_OFF_ATTRIBUTE not in other.attributes
    assert sm.get("binary_sensor.missing") is None
