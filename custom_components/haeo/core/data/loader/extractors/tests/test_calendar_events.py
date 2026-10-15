"""Tests for reading injected calendar events as a stepped forecast."""

from datetime import UTC, datetime, timedelta

import pytest

from conftest import FakeEntityState
from custom_components.haeo.core.data.loader import extractors
from custom_components.haeo.core.data.loader.calendar import CALENDAR_EVENTS_ATTRIBUTE
from custom_components.haeo.core.data.loader.extractors.calendar_events import Parser
from custom_components.haeo.core.data.util.input_values import InputError

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
def test_calendar_without_values_reads_as_zero(events: list[dict[str, str | None]]) -> None:
    """A calendar whose events hold no number reads as zero throughout."""
    assert extractors.extract(_state(events)).data == 0.0


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


@pytest.mark.parametrize(
    ("summaries", "translation_key"),
    [
        pytest.param(["0.5"], "calendar_value_without_unit", id="bare_number"),
        pytest.param(["1 kW", "1 kWh"], "calendar_mixed_units", id="mixed_units"),
    ],
)
def test_event_values_that_cannot_be_read_are_rejected(summaries: list[str], translation_key: str) -> None:
    """A bare number is not taken to be in base units, and events in different kinds of unit cannot sum."""
    with pytest.raises(InputError) as err:
        Parser.extract(_state([_event(i, i + 1, summary) for i, summary in enumerate(summaries)]))

    assert err.value.translation_key == translation_key


def test_calendar_without_injected_events_is_not_detected() -> None:
    """A plain calendar state without injected events is not read as a calendar forecast."""
    assert not Parser.detect(FakeEntityState(ENTITY_ID, "off", {}))
