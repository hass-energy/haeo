"""Tests for keeping a switch input's on periods."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.core import HomeAssistant, State

from custom_components.haeo.core.data.loader.switch import ON_PERIODS_ATTRIBUTE, OnPeriod
from custom_components.haeo.switch_history import LOOKBACK, SwitchHistory, _recorded_states, async_on_periods_at

SWITCH = "binary_sensor.dishwasher_running"
NOW = datetime(2026, 10, 20, 12, tzinfo=UTC)


def _periods(history: SwitchHistory) -> list[OnPeriod]:
    periods = history.attributes()[SWITCH][ON_PERIODS_ATTRIBUTE]
    assert isinstance(periods, list)
    return periods


def _state(value: str, at: datetime) -> State:
    return State(SWITCH, value, last_changed=at, last_updated=at)


def _recorder(result: dict[str, list[State]] | Exception) -> Mock:
    """Return a recorder instance whose executor jobs return the given recorded states or raise."""

    async def run(_func: Callable[..., object], *_args: object) -> object:
        if isinstance(result, Exception):
            raise result
        return result

    recorder = Mock()
    recorder.async_add_executor_job = AsyncMock(side_effect=run)
    return recorder


async def test_without_the_recorder_periods_start_at_the_live_state(hass: HomeAssistant) -> None:
    """Without the recorder a switch that is on counts from when its live state switched on."""
    hass.states.async_set(SWITCH, "on")
    switched_on = hass.states.get(SWITCH)
    assert switched_on is not None
    history = SwitchHistory(hass, [SWITCH])

    await history.async_load()

    assert _periods(history) == [(switched_on.last_changed_timestamp, None)]


async def test_live_changes_open_and_close_periods(hass: HomeAssistant) -> None:
    """Switching on opens a period and switching off closes it; other states neither."""
    hass.states.async_set(SWITCH, "off")
    history = SwitchHistory(hass, [SWITCH])
    await history.async_load()

    for value, minutes in (("on", 0), ("unavailable", 5), ("on", 6), ("off", 30)):
        history.record(SWITCH, _state(value, NOW + timedelta(minutes=minutes)))

    assert _periods(history) == [(NOW.timestamp(), (NOW + timedelta(minutes=30)).timestamp())]


async def test_recorded_states_seed_the_periods(hass: HomeAssistant) -> None:
    """The recorded states over the lookback seed the periods before the live state extends them."""
    hass.config.components.add("recorder")
    hass.states.async_set(SWITCH, "off")
    recorded = {SWITCH: [_state("on", NOW - timedelta(hours=2)), _state("off", NOW - timedelta(hours=1))]}
    history = SwitchHistory(hass, [SWITCH])

    with patch("custom_components.haeo.switch_history.get_instance", return_value=_recorder(recorded)):
        await history.async_load()

    assert _periods(history) == [((NOW - timedelta(hours=2)).timestamp(), (NOW - timedelta(hours=1)).timestamp())]


async def test_a_failed_recorder_query_keeps_only_the_live_state(hass: HomeAssistant) -> None:
    """A recorder query that fails leaves only what the live state shows."""
    hass.config.components.add("recorder")
    hass.states.async_set(SWITCH, "off")
    history = SwitchHistory(hass, [SWITCH])

    with patch("custom_components.haeo.switch_history.get_instance", return_value=_recorder(RuntimeError("boom"))):
        await history.async_load()

    assert _periods(history) == []


async def test_periods_older_than_the_lookback_are_dropped(hass: HomeAssistant) -> None:
    """Closed periods that ended before the lookback are dropped as new states arrive."""
    hass.states.async_set(SWITCH, "off")
    history = SwitchHistory(hass, [SWITCH])
    await history.async_load()

    history.record(SWITCH, _state("on", NOW - LOOKBACK - timedelta(hours=2)))
    history.record(SWITCH, _state("off", NOW - LOOKBACK - timedelta(hours=1)))
    history.record(SWITCH, _state("on", NOW))

    assert _periods(history) == [(NOW.timestamp(), None)]


async def test_on_periods_at_a_past_time(hass: HomeAssistant) -> None:
    """Historical diagnostics read the periods over the lookback ending at the run, or none when that fails."""
    recorded = {SWITCH: [_state("on", NOW - timedelta(minutes=20))]}

    with patch("custom_components.haeo.switch_history.get_instance", return_value=_recorder(recorded)):
        assert await async_on_periods_at(hass, SWITCH, NOW) == [((NOW - timedelta(minutes=20)).timestamp(), None)]

    with patch("custom_components.haeo.switch_history.get_instance", return_value=_recorder(RuntimeError("boom"))):
        assert await async_on_periods_at(hass, SWITCH, NOW) is None


def test_recorded_states_query_each_switch(hass: HomeAssistant) -> None:
    """Each switch's state changes are queried with its state at the window's start."""
    start = NOW - LOOKBACK
    changes = Mock(side_effect=lambda _hass, _start, _end, entity_id, **_kwargs: {entity_id: [_state("on", NOW)]})

    with patch("custom_components.haeo.switch_history.recorder_history.state_changes_during_period", changes):
        recorded = _recorded_states(hass, [SWITCH, "binary_sensor.other"], start, NOW)

    assert set(recorded) == {SWITCH, "binary_sensor.other"}
    assert changes.call_args.kwargs["include_start_time_state"] is True
