"""Home Assistant-backed state machine adapter."""

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


__all__ = ["HomeAssistantStateMachine"]
