"""Resolve a switch input: how long ago its switches first switched on in the open calendar window.

A switch, such as an appliance's running sensor, only says whether it is on
now. When a load started depends on its past states, so the integration reads
the switch's recorded states and injects the periods it was on into its state
as ``(start, end)`` pairs, the same way calendar events are injected into a
calendar's state. A switch input reads its window calendars as well as its
switches, so its captured source states hold both, and diagnostics replay the
same value.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
import math
from typing import Final

from custom_components.haeo.core.state import EntityState, StateMachine

from .calendar import CalendarEventData, load_calendar_events, open_window_start

# State attribute carrying a switch's on periods, injected by the integration
ON_PERIODS_ATTRIBUTE: Final = "haeo_on_periods"

# A period a switch was on: (start, end), POSIX seconds, end None while still on
type OnPeriod = tuple[float, float | None]

_SECONDS_PER_HOUR: Final = 3600.0

# Readings at or above this are on, matching how availability values are read
_ON_THRESHOLD: Final = 0.5

_WORDS: Final[dict[str, bool]] = {"on": True, "true": True, "off": False, "false": False}


def switch_state(raw: str) -> bool | None:
    """Return whether a state string reads as on, or None when it reads neither on nor off.

    States such as 'unavailable' or 'unknown' are neither, so a restart that
    briefly reads them neither starts nor ends an on period.
    """
    word = _WORDS.get(raw.strip().lower())
    if word is not None:
        return word
    try:
        value = float(raw)
    except ValueError:
        return None
    return value >= _ON_THRESHOLD if math.isfinite(value) else None


def _time(value: object) -> float | None:
    """Return a finite POSIX time, or None when the value is not one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


def read_on_periods(state: EntityState | None) -> list[OnPeriod] | None:
    """Return the on periods injected into a switch's state, oldest first, or None when it carries none."""
    raw = state.attributes.get(ON_PERIODS_ATTRIBUTE) if state is not None else None
    if not isinstance(raw, Sequence) or isinstance(raw, str):
        return None
    periods: list[OnPeriod] = []
    for item in raw:
        if not isinstance(item, Sequence) or isinstance(item, str) or len(item) != 2:  # noqa: PLR2004 (a pair)
            return None
        start, end = _time(item[0]), _time(item[1])
        if start is None or (item[1] is not None and end is None):
            return None
        periods.append((start, end))
    return sorted(periods)


def first_on_since(periods: Sequence[OnPeriod], since: float) -> float | None:
    """Return when a switch first switched on in a window that opened at *since*, or None when it has not.

    A switch already on when the window opened counts from when it switched
    on, as the run it is in started then.
    """
    return next((start for start, end in periods if end is None or end > since), None)


def resolve_switch(entity_ids: Sequence[str], sm: StateMachine, forecast_times: Sequence[float]) -> float | None:
    """Return how many hours before the horizon start the switches first switched on in the open window.

    The entities are the input's switches and its window calendars, told
    apart by the calendars' events. Overlapping events chain into one
    window, as for every calendar input. With several switches, the earliest
    switch-on counts. The value is 0 when no switch has switched on in the
    window, or no window is open. Returns None when a source has no state or
    a switch carries no on periods.
    """
    states = [sm.get(entity_id) for entity_id in entity_ids]
    if not forecast_times or any(state is None for state in states):
        return None
    events: list[CalendarEventData] = []
    switches: list[list[OnPeriod] | None] = []
    for state in states:
        found = load_calendar_events(state)
        if found is not None:
            events.extend(found)
        else:
            switches.append(read_on_periods(state))
    if any(periods is None for periods in switches):
        return None
    horizon_start = forecast_times[0]
    opened = open_window_start(events, datetime.fromtimestamp(horizon_start, tz=UTC))
    if opened is None:
        return 0.0
    starts = [start for periods in switches if periods and (start := first_on_since(periods, opened)) is not None]
    if not starts:
        return 0.0
    return max(horizon_start - min(starts), 0.0) / _SECONDS_PER_HOUR


__all__ = [
    "ON_PERIODS_ATTRIBUTE",
    "OnPeriod",
    "first_on_since",
    "read_on_periods",
    "resolve_switch",
    "switch_state",
]
