"""Home Assistant-backed state machine adapter."""

from collections.abc import Mapping
from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.haeo.core.state import EntityState, StateMachine


class HomeAssistantStateMachine(StateMachine):
    """Read entity state from Home Assistant's state machine."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the state machine adapter."""
        self._hass = hass

    def get(self, entity_id: str) -> EntityState | None:
        """Return current state for *entity_id*."""
        return self._hass.states.get(entity_id)


class AnnotatedState:
    """EntityState wrapper that merges extra attributes into a base state.

    Lets the integration hand the core loader data Home Assistant does not
    keep on the state itself, such as fetched calendar events or recorder
    history, in the same form diagnostics capture and replay.
    """

    def __init__(self, base: EntityState, extra_attributes: Mapping[str, Any]) -> None:
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
    def attributes(self) -> Mapping[str, Any]:
        """Entity attributes with the extra attributes merged in."""
        return {**self._base.attributes, **self._extra_attributes}

    def as_dict(self) -> dict[str, Any]:
        """Return serialized state representation including the extra attributes."""
        base = self._base.as_dict()
        attributes = {**base.get("attributes", {}), **self._extra_attributes}
        return {**base, "attributes": attributes}


__all__ = ["AnnotatedState", "HomeAssistantStateMachine"]
