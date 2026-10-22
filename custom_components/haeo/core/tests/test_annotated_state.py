"""Tests for the state machines that merge extra attributes into entity states."""

from collections.abc import Callable, Mapping
from typing import Never
from zoneinfo import ZoneInfo

import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.annotated_state import AnnotatedStateMachine, CalendarStateMachine
from custom_components.haeo.core.data.loader.calendar import CALENDAR_EVENTS_ATTRIBUTE, CalendarEventDict
from custom_components.haeo.core.state import StateMachine

ENTITY_ID = "calendar.trips"


def test_state_machine_injects_events_for_known_calendars() -> None:
    """Known calendar entities get events merged into their attributes."""
    base = FakeStateMachine({ENTITY_ID: FakeEntityState(ENTITY_ID, "on", {"existing": 1})})
    events = [
        CalendarEventDict(
            start="2026-01-01T00:00:00+00:00",
            end="2026-01-01T01:00:00+00:00",
            summary="Trip",
            location=None,
            description=None,
        )
    ]
    sm = CalendarStateMachine(base, {ENTITY_ID: events})

    state = sm.get(ENTITY_ID)

    assert state is not None
    assert state.entity_id == ENTITY_ID
    assert state.state == "on"
    assert state.attributes["existing"] == 1
    assert state.attributes[CALENDAR_EVENTS_ATTRIBUTE] == events
    serialized_attributes = state.as_dict()["attributes"]
    assert isinstance(serialized_attributes, Mapping)
    assert serialized_attributes[CALENDAR_EVENTS_ATTRIBUTE] == events


def test_state_machine_passes_through_other_entities() -> None:
    """Entities without event lists are returned unmodified."""
    base = FakeStateMachine({"sensor.x": FakeEntityState("sensor.x", "1.0", {})})
    sm = CalendarStateMachine(base, {})

    state = sm.get("sensor.x")

    assert state is not None
    assert CALENDAR_EVENTS_ATTRIBUTE not in state.attributes
    assert sm.get("sensor.missing") is None


def test_state_machine_reads_a_calendar_without_events_as_missing() -> None:
    """A calendar whose events were not fetched reads as missing, not as its plain state."""
    base = FakeStateMachine({ENTITY_ID: FakeEntityState(ENTITY_ID, "off", {})})
    sm = CalendarStateMachine(base, {ENTITY_ID: None})

    assert sm.get(ENTITY_ID) is None


@pytest.mark.parametrize("decorator", [AnnotatedStateMachine, CalendarStateMachine])
def test_state_machine_reads_in_the_base_time_zone(
    decorator: Callable[[StateMachine, Mapping[str, Never]], StateMachine],
) -> None:
    """A decorated state machine reads naive times in its base's time zone."""
    adelaide = ZoneInfo("Australia/Adelaide")

    assert decorator(FakeStateMachine({}, time_zone=adelaide), {}).time_zone is adelaide
