"""Read entities whose states are words as on or off.

An on/off input, such as whether an EV is plugged in, normally reads binary
sensors. Some integrations report the same thing as words instead, such as a
charger reporting ``Charging``, ``Occupied``, or ``Idle``. The input's value
then lists which states mean on and which mean off, and this state machine
rewrites those entities' states to ``on`` and ``off`` before the loader reads
them. Captured states keep the words, so diagnostics replay the same reading.
"""

from collections.abc import Mapping, Sequence
from datetime import tzinfo
from typing import Final

from custom_components.haeo.core.schema import EntityValue
from custom_components.haeo.core.state import NO_READING_STATES, ON_OFF_STATE_VALUES, EntityState, StateMachine

# The state an entity reads when its word is in neither list
_UNMATCHED: Final = "unknown"


def on_off_state(state: str, on_states: Sequence[str], off_states: Sequence[str]) -> str:
    """Return ``on`` or ``off`` for a state, from the states listed as meaning each.

    With only one list given, every other state means the opposite. With
    both, a state in neither has no reading, as Home Assistant's own
    ``unknown`` does. A state without a reading is kept as it is. A state
    that already reads as on or off keeps its reading unless it is listed, so
    a binary sensor beside a sensor reporting words still reads the same.
    """
    if state in NO_READING_STATES:
        return state
    if state in on_states:
        return "on"
    if state in off_states:
        return "off"
    if state.lower() in ON_OFF_STATE_VALUES:
        return state
    if on_states and not off_states:
        return "off"
    if off_states and not on_states:
        return "on"
    return _UNMATCHED


class _OnOffState:
    """An entity state with its word read as on or off."""

    def __init__(self, base: EntityState, state: str) -> None:
        self._base = base
        self._state = state

    @property
    def entity_id(self) -> str:
        """Entity identifier."""
        return self._base.entity_id

    @property
    def state(self) -> str:
        """The state read as on or off."""
        return self._state

    @property
    def attributes(self) -> Mapping[str, object]:
        """Entity attributes."""
        return self._base.attributes

    def as_dict(self) -> Mapping[str, object]:
        """Return the serialized state, with the state read as on or off."""
        return {**self._base.as_dict(), "state": self._state}


class OnOffStateMachine:
    """State machine decorator that reads an input's entities as on or off from the states it lists."""

    def __init__(self, base: StateMachine, value: EntityValue) -> None:
        """Initialize with a base state machine and the input's entity value."""
        self._base = base
        self._entity_ids = frozenset(value["value"])
        self._on_states = tuple(value.get("on_states", ()))
        self._off_states = tuple(value.get("off_states", ()))

    @property
    def time_zone(self) -> tzinfo:
        """Return the base state machine's time zone."""
        return self._base.time_zone

    def get(self, entity_id: str) -> EntityState | None:
        """Return the entity state, read as on or off when it is one of the input's entities."""
        state = self._base.get(entity_id)
        if state is None or entity_id not in self._entity_ids:
            return state
        return _OnOffState(state, on_off_state(state.state, self._on_states, self._off_states))


def lists_on_off_states(value: EntityValue) -> bool:
    """Return True when an entity value lists the states that mean on or off."""
    return bool(value.get("on_states") or value.get("off_states"))


__all__ = ["OnOffStateMachine", "lists_on_off_states", "on_off_state"]
