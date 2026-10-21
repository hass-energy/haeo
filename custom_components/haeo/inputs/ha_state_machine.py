"""Home Assistant-backed state machine adapter."""

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


__all__ = ["HomeAssistantStateMachine"]
