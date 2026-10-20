"""Tests for reading when a switch first switched on in a calendar window."""

from datetime import UTC, datetime

import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.data.loader.calendar import CALENDAR_EVENTS_ATTRIBUTE
from custom_components.haeo.core.data.loader.switch import (
    ON_PERIODS_ATTRIBUTE,
    OnPeriod,
    first_on_since,
    read_on_periods,
    resolve_switch,
    switch_state,
)

SWITCH = "binary_sensor.dishwasher_running"
CALENDAR = "calendar.dishwasher"
HORIZON_START = 36_000.0


def _state(attributes: dict[str, object]) -> FakeEntityState:
    return FakeEntityState(SWITCH, "on", attributes)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param("on", True, id="on"),
        pytest.param("True", True, id="true_word"),
        pytest.param("off", False, id="off"),
        pytest.param("1", True, id="one"),
        pytest.param("0", False, id="zero"),
        pytest.param("unavailable", None, id="unavailable"),
        pytest.param("nan", None, id="not_finite"),
    ],
)
def test_switch_state(raw: str, expected: bool | None) -> None:
    """On/off words and numbers read as on or off; anything else reads as neither."""
    assert switch_state(raw) is expected


def test_read_on_periods_sorts_the_injected_pairs() -> None:
    """Injected periods read as (start, end) pairs, oldest first, with None for one still on."""
    state = _state({ON_PERIODS_ATTRIBUTE: [[300.0, None], [100.0, 200.0]]})

    assert read_on_periods(state) == [(100.0, 200.0), (300.0, None)]


@pytest.mark.parametrize(
    "attributes",
    [
        pytest.param({}, id="no_periods"),
        pytest.param({ON_PERIODS_ATTRIBUTE: "1,2"}, id="not_a_list"),
        pytest.param({ON_PERIODS_ATTRIBUTE: [[100.0]]}, id="not_a_pair"),
        pytest.param({ON_PERIODS_ATTRIBUTE: [[100.0, "x"]]}, id="end_not_a_number"),
        pytest.param({ON_PERIODS_ATTRIBUTE: [[None, 100.0]]}, id="no_start"),
        pytest.param({ON_PERIODS_ATTRIBUTE: [[True, 100.0]]}, id="boolean_start"),
    ],
)
def test_read_on_periods_rejects_states_without_usable_periods(attributes: dict[str, object]) -> None:
    """A state without well-formed periods carries none."""
    assert read_on_periods(_state(attributes)) is None


@pytest.mark.parametrize(
    ("periods", "expected"),
    [
        pytest.param([(100.0, 150.0), (300.0, 400.0)], 300.0, id="first_switch_on_after_opening"),
        pytest.param([(150.0, 250.0), (300.0, None)], 150.0, id="on_when_the_window_opened"),
        pytest.param([(100.0, 200.0)], None, id="off_before_the_window_opened"),
        pytest.param([], None, id="never_on"),
    ],
)
def test_first_on_since(periods: list[OnPeriod], expected: float | None) -> None:
    """The first switch-on counts from the window opening, or from when it switched on if on then."""
    assert first_on_since(periods, 200.0) == expected


def _event(start: float, end: float) -> dict[str, object]:
    return {
        "start": datetime.fromtimestamp(start, tz=UTC).isoformat(),
        "end": datetime.fromtimestamp(end, tz=UTC).isoformat(),
        "summary": "Dishwasher",
        "location": None,
        "description": None,
    }


def _resolve(periods: list[OnPeriod] | None, events: list[dict[str, object]]) -> float | None:
    states = {CALENDAR: FakeEntityState(CALENDAR, "on", {CALENDAR_EVENTS_ATTRIBUTE: events})}
    states[SWITCH] = _state({} if periods is None else {ON_PERIODS_ATTRIBUTE: periods})
    return resolve_switch([SWITCH, CALENDAR], FakeStateMachine(states), (HORIZON_START, HORIZON_START + 3600.0))


@pytest.mark.parametrize(
    ("periods", "events", "expected"),
    [
        pytest.param(
            [(HORIZON_START - 1800.0, None)],
            [_event(HORIZON_START - 3600.0, HORIZON_START + 3600.0)],
            0.5,
            id="running_since_half_an_hour_ago",
        ),
        pytest.param(
            [(HORIZON_START - 2700.0, HORIZON_START - 900.0)],
            [_event(HORIZON_START - 3600.0, HORIZON_START + 3600.0)],
            0.75,
            id="ran_earlier_in_the_window",
        ),
        pytest.param(
            [(HORIZON_START - 7200.0, HORIZON_START - 5400.0)],
            [_event(HORIZON_START - 3600.0, HORIZON_START + 3600.0)],
            0.0,
            id="ran_before_the_window",
        ),
        pytest.param(
            [(HORIZON_START - 1800.0, None)],
            [_event(HORIZON_START + 600.0, HORIZON_START + 3600.0)],
            0.0,
            id="no_window_open",
        ),
        pytest.param([], [_event(HORIZON_START - 3600.0, HORIZON_START + 3600.0)], 0.0, id="never_on"),
        pytest.param(None, [_event(HORIZON_START - 3600.0, HORIZON_START + 3600.0)], None, id="no_periods_injected"),
    ],
)
def test_resolve_switch(
    periods: list[OnPeriod] | None, events: list[dict[str, object]], expected: float | None
) -> None:
    """A switch input resolves to the hours since its switch first switched on in the open window."""
    assert _resolve(periods, events) == (None if expected is None else pytest.approx(expected))


def test_resolve_switch_takes_the_earliest_of_several_switches() -> None:
    """With several switches, the earliest switch-on in the window counts."""
    states = {
        CALENDAR: FakeEntityState(
            CALENDAR, "on", {CALENDAR_EVENTS_ATTRIBUTE: [_event(HORIZON_START - 3600.0, HORIZON_START + 3600.0)]}
        ),
        SWITCH: _state({ON_PERIODS_ATTRIBUTE: [(HORIZON_START - 900.0, None)]}),
        "binary_sensor.other": FakeEntityState(
            "binary_sensor.other", "off", {ON_PERIODS_ATTRIBUTE: [(HORIZON_START - 1800.0, HORIZON_START - 1200.0)]}
        ),
    }

    resolved = resolve_switch(
        [SWITCH, "binary_sensor.other", CALENDAR], FakeStateMachine(states), (HORIZON_START, HORIZON_START + 3600.0)
    )

    assert resolved == pytest.approx(0.5)


def test_resolve_switch_with_a_missing_source() -> None:
    """A source without a state leaves the input unresolved."""
    assert resolve_switch([SWITCH, CALENDAR], FakeStateMachine({}), (HORIZON_START, HORIZON_START + 3600.0)) is None
