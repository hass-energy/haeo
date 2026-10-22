"""State machines that merge data Home Assistant does not keep on a state into it.

The integration fetches calendar events and recorded meter totals and hands
them to the core loader as extra state attributes, in the same form
diagnostics capture and replay, so live runs and replays read inputs the same way.
"""

from collections.abc import Mapping
from datetime import tzinfo

from custom_components.haeo.core.data.loader.calendar import CALENDAR_EVENTS_ATTRIBUTE, CalendarEventDict
from custom_components.haeo.core.state import EntityState, StateMachine


def is_calendar_entity(entity_id: str) -> bool:
    """Return True when an entity is a calendar."""
    return entity_id.startswith("calendar.")


class AnnotatedState:
    """EntityState wrapper that merges extra attributes into a base state.

    Lets the integration hand the core loader data Home Assistant does not
    keep on the state itself, such as fetched calendar events or a meter's
    recorded totals, in the same form diagnostics capture and replay.
    """

    def __init__(self, base: EntityState, extra_attributes: Mapping[str, object]) -> None:
        """Initialize with the base state and the attributes to merge in."""
        self._base = base
        self._extra_attributes = extra_attributes

    @property
    def entity_id(self) -> str:
        """Entity identifier."""
        return self._base.entity_id

    @property
    def state(self) -> str:
        """Raw state string."""
        return self._base.state

    @property
    def attributes(self) -> Mapping[str, object]:
        """Entity attributes with the extra attributes merged in."""
        return {**self._base.attributes, **self._extra_attributes}

    def as_dict(self) -> Mapping[str, object]:
        """Return serialized state representation including the extra attributes."""
        return {**self._base.as_dict(), "attributes": self.attributes}


class AnnotatedStateMachine(StateMachine):
    """State machine decorator that merges extra attributes into the states of the entities it knows."""

    def __init__(self, base: StateMachine, attributes: Mapping[str, Mapping[str, object]]) -> None:
        """Initialize with a base state machine and the extra attributes per entity."""
        self._base = base
        self._attributes = attributes

    @property
    def time_zone(self) -> tzinfo:
        """Return the base state machine's time zone."""
        return self._base.time_zone

    def get(self, entity_id: str) -> EntityState | None:
        """Return the entity state, with its extra attributes merged when known."""
        state = self._base.get(entity_id)
        extra = self._attributes.get(entity_id)
        if state is None or extra is None:
            return state
        return AnnotatedState(state, extra)


class CalendarStateMachine(StateMachine):
    """State machine decorator that augments calendar entities with events.

    A calendar without fetched events, because its fetch failed or has not
    run yet, reads as unavailable rather than as an empty calendar, unless its
    state already carries events, as a replayed diagnostics or scenario state
    does. Its plain state would otherwise read as a number.
    """

    def __init__(self, base: StateMachine, events_by_entity: Mapping[str, list[CalendarEventDict] | None]) -> None:
        """Initialize with a base state machine and per-entity event lists."""
        self._base = base
        self._events_by_entity = events_by_entity

    @property
    def time_zone(self) -> tzinfo:
        """Return the base state machine's time zone."""
        return self._base.time_zone

    def get(self, entity_id: str) -> EntityState | None:
        """Return the entity state, with events merged for known calendars."""
        state = self._base.get(entity_id)
        if state is None or not is_calendar_entity(entity_id):
            return state
        events = self._events_by_entity.get(entity_id)
        if events is None:
            return state if CALENDAR_EVENTS_ATTRIBUTE in state.attributes else None
        return AnnotatedState(state, {CALENDAR_EVENTS_ATTRIBUTE: events})


__all__ = ["AnnotatedState", "AnnotatedStateMachine", "CalendarStateMachine", "is_calendar_entity"]
