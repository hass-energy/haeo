"""Home Assistant-backed state machine adapter."""

from collections.abc import Mapping
from datetime import tzinfo

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.haeo.core.state import EntityState, StateMachine


class HomeAssistantStateMachine(StateMachine):
    """Read entity state from Home Assistant's state machine."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the state machine adapter."""
        self._hass = hass

    @property
    def time_zone(self) -> tzinfo:
        """Return Home Assistant's configured time zone."""
        return dt_util.get_default_time_zone()

    def get(self, entity_id: str) -> EntityState | None:
        """Return current state for *entity_id*."""
        return self._hass.states.get(entity_id)


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


__all__ = ["AnnotatedState", "AnnotatedStateMachine", "HomeAssistantStateMachine"]
