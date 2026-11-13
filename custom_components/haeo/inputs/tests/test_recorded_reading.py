"""Tests for looking up a source's last recorded reading."""

from collections.abc import Callable
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.core import HomeAssistant, State
import pytest

from custom_components.haeo.inputs.recorded_reading import async_last_recorded_reading, last_recorded_reading

SENSOR = "sensor.ev_soc"
AT = datetime(2025, 1, 1, 12, tzinfo=UTC)


def _recorder(result: State | None | Exception) -> Mock:
    """Return a recorder instance whose executor jobs return the given state or raise."""

    async def run(_func: Callable[..., object], *_args: object) -> object:
        if isinstance(result, Exception):
            raise result
        return result

    recorder = Mock()
    recorder.async_add_executor_job = AsyncMock(side_effect=run)
    return recorder


@pytest.mark.parametrize(
    ("recorded", "expected"),
    [
        pytest.param(["40", "unavailable", "41", "unknown", "unavailable"], "41", id="latest_with_a_reading"),
        pytest.param(["unavailable", "unknown"], None, id="none_with_a_reading"),
        pytest.param(None, None, id="not_recorded"),
    ],
)
def test_last_recorded_reading_is_the_latest_state_with_a_reading(
    hass: HomeAssistant, recorded: list[str] | None, expected: str | None
) -> None:
    """The latest recorded state with a reading is returned, skipping states without one."""
    changes = {} if recorded is None else {SENSOR: [State(SENSOR, state) for state in recorded]}

    with patch(
        "custom_components.haeo.inputs.recorded_reading.history.get_last_state_changes", return_value=changes
    ) as lookup:
        reading = last_recorded_reading(hass, SENSOR)

    assert (reading.state if reading is not None else None) == expected
    assert lookup.call_args.args[2] == SENSOR


async def test_last_recorded_reading_is_read_from_the_recorder(hass: HomeAssistant) -> None:
    """The lookup runs on the recorder's executor."""
    hass.config.components.add("recorder")
    recorded = State(SENSOR, "41", last_reported=AT)

    with patch("custom_components.haeo.inputs.recorded_reading.get_instance", return_value=_recorder(recorded)):
        assert await async_last_recorded_reading(hass, SENSOR) is recorded


@pytest.mark.parametrize("recorder_loaded", [False, True], ids=["without_recorder", "lookup_fails"])
async def test_last_recorded_reading_is_none_when_it_cannot_be_read(
    hass: HomeAssistant, *, recorder_loaded: bool
) -> None:
    """Without the recorder, or when the lookup fails, there is no recorded reading."""
    if recorder_loaded:
        hass.config.components.add("recorder")

    with patch(
        "custom_components.haeo.inputs.recorded_reading.get_instance", return_value=_recorder(RuntimeError("db"))
    ):
        assert await async_last_recorded_reading(hass, SENSOR) is None
