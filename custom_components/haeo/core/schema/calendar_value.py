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
    The ``events`` field is populated during loading with the raw event data,
    so diagnostics capture the exact events the optimizer used.
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
    return value.get("type") == VALUE_TYPE_CALENDAR


__all__ = [
    "CalendarEventDict",
    "CalendarValue",
    "as_calendar_value",
    "is_calendar_value",
]
