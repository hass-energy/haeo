"""State provider abstraction for entity state access."""

from collections.abc import Iterable
from datetime import datetime
from typing import Protocol

from homeassistant.core import HomeAssistant, State


class StateProvider(Protocol):
    """Protocol for retrieving entity states.

    Implementations can fetch current state or historical state
    from different data sources.
    """

    @property
    def is_historical(self) -> bool:
        """Return True if this provider fetches historical data."""
        ...

    @property
    def timestamp(self) -> datetime | None:
        """Return the timestamp for historical providers, None for current."""
        ...

    async def get_state(self, entity_id: str) -> State | None:
        """Get state for a single entity."""
        ...

    async def get_states(self, entity_ids: Iterable[str]) -> dict[str, State]:
        """Get states for multiple entities.

        Returns a dict mapping entity_id to State for entities that have state.
        Entities without state are omitted from the result.
        """
        ...


class CurrentStateProvider:
    """State provider that fetches current state from the state machine."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the provider."""
        self._hass = hass

    @property
    def is_historical(self) -> bool:
        """Return False - this provider fetches current state."""
        return False

    @property
    def timestamp(self) -> datetime | None:
        """Return None - current state has no specific timestamp."""
        return None

    async def get_state(self, entity_id: str) -> State | None:
        """Get current state for an entity."""
        return self._hass.states.get(entity_id)

    async def get_states(self, entity_ids: Iterable[str]) -> dict[str, State]:
        """Get current states for multiple entities."""
        result: dict[str, State] = {}
        for entity_id in entity_ids:
            state = self._hass.states.get(entity_id)
            if state is not None:
                result[entity_id] = state
        return result


__all__ = [
    "CurrentStateProvider",
    "StateProvider",
]
