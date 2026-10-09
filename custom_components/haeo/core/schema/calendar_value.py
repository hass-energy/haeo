"""Schema values for calendar-based inputs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, TypedDict, TypeGuard

VALUE_TYPE_CALENDAR = "calendar"


class CalendarEventDict(TypedDict):
    """Serialized calendar event for diagnostics capture."""

    start: str
    end: str
    summary: str | None
    location: str | None
    description: str | None


class CalendarValue(TypedDict):
    """Schema value representing calendar-based inputs.

    The ``value`` field contains the calendar entity ID.
    The ``events`` field is None for live configs; diagnostics capture writes
    the events the optimizer used (via ``capture_calendar_events``) so replay
    resolves identically without a live calendar entity.
    """

    type: Literal["calendar"]
    value: str
    events: Sequence[CalendarEventDict] | None


def as_calendar_value(entity_id: str) -> CalendarValue:
    """Create a calendar schema value from an entity ID."""
    return {"type": VALUE_TYPE_CALENDAR, "value": entity_id, "events": None}


def is_calendar_value(value: Any) -> TypeGuard[CalendarValue]:
    """Return True if value is a calendar schema value."""
    if not isinstance(value, Mapping):
        return False
    if value.get("type") != VALUE_TYPE_CALENDAR:
        return False
    return isinstance(value.get("value"), str)


__all__ = [
    "CalendarEventDict",
    "CalendarValue",
    "as_calendar_value",
    "is_calendar_value",
]
