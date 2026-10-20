"""Tests for keeping a meter input's running totals through resets."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.core.data.loader.meter import METER_TOTALS_ATTRIBUTE
from custom_components.haeo.meter_history import LOOKBACK, MeterHistory, async_meter_totals_at, recorded_totals

METER = "sensor.pump_energy"


def _totals(history: MeterHistory) -> list[tuple[float, float]]:
    attributes = history.attributes()[METER]
    totals = attributes[METER_TOTALS_ATTRIBUTE]
    assert isinstance(totals, list)
    return totals


def _recorder(result: tuple[list[tuple[float, float]], float | None] | Exception) -> Mock:
    """Return a recorder instance whose executor jobs return the given recorded totals or raise."""

    async def run(_func: Callable[..., object], *_args: object) -> object:
        if isinstance(result, Exception):
            raise result
        return result

    recorder = Mock()
    recorder.async_add_executor_job = AsyncMock(side_effect=run)
    return recorder


async def test_without_the_recorder_totals_start_at_the_live_reading(hass: HomeAssistant) -> None:
    """Without the recorder a meter's totals start from zero at its live reading and grow with each change."""
    hass.states.async_set(METER, "10")
    history = MeterHistory(hass, [METER])

    await history.async_load()
    hass.states.async_set(METER, "12")
    history.record(METER, hass.states.get(METER))

    assert [total for _at, total in _totals(history)] == [0.0, 2.0]


async def test_a_falling_reading_is_a_reset_that_rose_from_zero(hass: HomeAssistant) -> None:
    """A reading below the last is a reset, so the total grows by the new reading, as an "energy today" meter does."""
    hass.states.async_set(METER, "10")
    history = MeterHistory(hass, [METER])
    await history.async_load()

    for reading in ("12", "1", "3"):
        hass.states.async_set(METER, reading)
        history.record(METER, hass.states.get(METER))

    assert [total for _at, total in _totals(history)] == [0.0, 2.0, 3.0, 5.0]


async def test_readings_that_are_not_numbers_are_skipped(hass: HomeAssistant) -> None:
    """A meter reading unavailable adds nothing to its total."""
    hass.states.async_set(METER, "10")
    history = MeterHistory(hass, [METER])
    await history.async_load()

    hass.states.async_set(METER, "unavailable")
    history.record(METER, hass.states.get(METER))

    assert [total for _at, total in _totals(history)] == [0.0]


async def test_recorded_totals_continue_with_the_live_reading(hass: HomeAssistant) -> None:
    """Recorded totals carry on with the rise from the last recorded reading to the live one."""
    hass.config.components.add("recorder")
    hass.states.async_set(METER, "7")
    history = MeterHistory(hass, [METER])

    with patch("custom_components.haeo.meter_history.get_instance", return_value=_recorder(([(100.0, 40.0)], 5.0))):
        await history.async_load()

    totals = _totals(history)
    assert totals[0] == (100.0, 40.0)
    assert totals[-1][1] == pytest.approx(42.0)


async def test_a_failed_statistics_lookup_keeps_only_live_readings(hass: HomeAssistant) -> None:
    """A statistics lookup that fails leaves the meter with only its live readings."""
    hass.config.components.add("recorder")
    hass.states.async_set(METER, "7")
    history = MeterHistory(hass, [METER])

    with patch("custom_components.haeo.meter_history.get_instance", return_value=_recorder(RuntimeError("db"))):
        await history.async_load()

    assert [total for _at, total in _totals(history)] == [0.0]


async def test_totals_older_than_the_lookback_are_dropped(hass: HomeAssistant) -> None:
    """Totals older than the lookback before the latest reading are dropped, keeping one to start from."""
    hass.config.components.add("recorder")
    now = datetime.now(UTC).timestamp()
    old = now - LOOKBACK.total_seconds() - 3600.0
    hass.states.async_set(METER, "7")
    history = MeterHistory(hass, [METER])

    with patch(
        "custom_components.haeo.meter_history.get_instance",
        return_value=_recorder(([(old - 600.0, 30.0), (old, 35.0), (now - 600.0, 40.0)], 5.0)),
    ):
        await history.async_load()

    assert [total for _at, total in _totals(history)] == [35.0, 40.0, 42.0]


def test_recorded_totals_read_the_statistics_sums(hass: HomeAssistant) -> None:
    """Recorded totals are each 5-minute bucket's sum at its end, with the last bucket's reading."""
    rows = {
        METER: [
            {"start": 0.0, "end": 300.0, "sum": 1.0, "state": 4.0},
            {"start": 300.0, "end": 600.0, "sum": None, "state": None},
            {"start": 600.0, "end": 900.0, "sum": 2.5, "state": 5.5},
        ]
    }
    start = datetime(2026, 10, 20, tzinfo=UTC)

    with patch("custom_components.haeo.meter_history.statistics.statistics_during_period", return_value=rows) as lookup:
        totals, last_reading = recorded_totals(hass, METER, start, None)

    assert totals == [(300.0, 1.0), (900.0, 2.5)]
    assert last_reading == 5.5
    assert lookup.call_args.args[4] == "5minute"


async def test_totals_at_a_past_time_end_with_the_state_then(hass: HomeAssistant) -> None:
    """Historical totals end with the rise from the last recorded reading to the meter's state at that time."""
    at = datetime(2026, 10, 20, 12, tzinfo=UTC)
    hass.states.async_set(METER, "9")
    state = hass.states.get(METER)
    assert state is not None

    with patch(
        "custom_components.haeo.meter_history.get_instance",
        return_value=_recorder(([((at - timedelta(minutes=5)).timestamp(), 40.0)], 6.0)),
    ):
        totals = await async_meter_totals_at(hass, METER, at, state)

    assert totals[-1] == (at.timestamp(), 43.0)
