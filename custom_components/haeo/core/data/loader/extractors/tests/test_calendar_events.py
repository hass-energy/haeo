"""Tests for reading injected calendar events as a stepped forecast."""

from datetime import UTC, datetime, timedelta

import pytest

from conftest import FakeEntityState
from custom_components.haeo.core.data.loader import extractors
from custom_components.haeo.core.data.loader.calendar import CALENDAR_EVENTS_ATTRIBUTE
from custom_components.haeo.core.data.loader.extractors.calendar_events import Parser
from custom_components.haeo.core.model.const import OutputType

ENTITY_ID = "calendar.demand"

PADDING = timedelta(days=60).total_seconds()


def _event(start_h: float, end_h: float, summary: str) -> dict[str, str | None]:
    """Build an injected event dict spanning the given hours after epoch 0."""
    return {
        "start": datetime.fromtimestamp(start_h * 3600.0, tz=UTC).isoformat(),
        "end": datetime.fromtimestamp(end_h * 3600.0, tz=UTC).isoformat(),
        "summary": summary,
        "location": None,
        "description": None,
    }


def _state(events: list[dict[str, str | None]]) -> FakeEntityState:
    return FakeEntityState(ENTITY_ID, "off", {CALENDAR_EVENTS_ATTRIBUTE: events})


def test_events_step_between_their_values() -> None:
    """Each event holds its value while it runs and zero outside it."""
    data, unit, _ = Parser.extract(_state([_event(1, 2, "0.5 kW")]))

    assert data == [
        (3600.0 - PADDING, 0.0),
        (3600.0, 0.0),
        (3600.0, 0.5),
        (7200.0, 0.5),
        (7200.0, 0.0),
        (7200.0 + PADDING, 0.0),
    ]
    assert unit == "kW"


def test_overlapping_events_sum() -> None:
    """Overlapping events add together while both run."""
    data, _, _ = Parser.extract(_state([_event(0, 2, "1 kW"), _event(1, 3, "2000 W")]))

    assert isinstance(data, list)
    assert data[1:-1] == [
        (0.0, 0.0),
        (0.0, 1.0),
        (3600.0, 1.0),
        (3600.0, 3.0),
        (7200.0, 3.0),
        (7200.0, 2.0),
        (10800.0, 2.0),
        (10800.0, 0.0),
    ]


def test_extract_reads_events_as_a_step_forecast() -> None:
    """The dispatcher reads injected events, separating each step so the fuser does not ramp across it."""
    result = extractors.extract(_state([_event(1, 2, "0.5 kW")]))

    assert isinstance(result.data, list)
    times = [point[0] for point in result.data]
    assert times == sorted(times)
    assert len(set(times)) == len(times)
    assert [point[1] for point in result.data] == [0.0, 0.0, 0.5, 0.5, 0.0, 0.0]
    assert result.data[1][0] == pytest.approx(3600.0)
    assert result.data[-2][0] == pytest.approx(7200.0)


@pytest.mark.parametrize(
    "events",
    [
        pytest.param([], id="no_events"),
        pytest.param([_event(0, 1, "Holiday")], id="events_without_values"),
    ],
)
def test_calendar_without_values_is_a_forecast_with_no_points(events: list[dict[str, str | None]]) -> None:
    """A calendar whose events hold no number is a forecast with no points, not a present value of zero."""
    assert extractors.extract(_state(events)).data == []


@pytest.mark.parametrize(
    ("summary", "expected"),
    [
        pytest.param("500 W", (0.5, "kW"), id="power"),
        pytest.param("0.30 AUD/kWh", (0.30, "AUD/kWh"), id="price_per_kwh"),
        pytest.param("120 €/MWh", (0.12, "€/kWh"), id="price_per_mwh"),
        pytest.param("30 min", (0.5, "h"), id="duration"),
    ],
)
def test_event_values_convert_to_base_units(summary: str, expected: tuple[float, str]) -> None:
    """An event's value converts from the unit typed with it to base units, like a sensor reading."""
    data, unit, _ = Parser.extract(_state([_event(1, 2, summary)]))

    assert isinstance(data, list)
    assert data[2][1] == pytest.approx(expected[0])
    assert unit == expected[1]


def test_events_the_input_cannot_use_are_ignored() -> None:
    """Read against an input's unit, events whose values it cannot use are ignored rather than failing the input."""
    state = _state([_event(0, 1, "0.5"), _event(1, 2, "1 kWh"), _event(2, 3, "2000 W")])

    data, unit, _ = Parser.extract(state, OutputType.POWER)

    assert isinstance(data, list)
    assert [value for _, value in data[1:-1]] == [0.0, 2.0, 2.0, 0.0]
    assert unit is None


def test_without_an_input_events_keep_the_first_events_base_unit() -> None:
    """Read without an input, bare numbers and events in another kind of unit are left out."""
    state = _state([_event(0, 1, "0.5"), _event(1, 2, "1 kW"), _event(2, 3, "1 kWh")])

    data, unit, _ = Parser.extract(state)

    assert isinstance(data, list)
    assert [value for _, value in data[1:-1]] == [0.0, 1.0, 1.0, 0.0]
    assert unit == "kW"


def test_calendar_without_injected_events_is_not_detected() -> None:
    """A plain calendar state without injected events is not read as a calendar forecast."""
    assert not Parser.detect(FakeEntityState(ENTITY_ID, "off", {}))
