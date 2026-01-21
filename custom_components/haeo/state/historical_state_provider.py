"""Historical state provider using the recorder."""

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Any, cast

from homeassistant.components.recorder import history as recorder_history
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.recorder import get_instance as get_recorder_instance


class HistoricalStateProvider:
    """State provider that fetches historical state from the recorder."""

    def __init__(
        self,
        hass: HomeAssistant,
        target_timestamp: datetime,
    ) -> None:
        """Initialize the provider.

        Args:
            hass: Home Assistant instance
            target_timestamp: The timestamp to fetch state for

        """
        self._hass = hass
        self._timestamp = target_timestamp
        self._recorder = get_recorder_instance(hass)

    @property
    def is_historical(self) -> bool:
        """Return True - this provider fetches historical state."""
        return True

    @property
    def timestamp(self) -> datetime | None:
        """Return the target timestamp."""
        return self._timestamp

    async def get_state(self, entity_id: str) -> State | None:
        """Get historical state for a single entity."""
        states = await self.get_states([entity_id])
        return states.get(entity_id)

    async def get_states(self, entity_ids: Iterable[str]) -> dict[str, State]:
        """Get historical states for multiple entities.

        Uses the recorder history API with include_start_time_state=True
        to get the most recent state AT or BEFORE the target timestamp.
        """
        entity_id_list = list(entity_ids)
        if not entity_id_list:
            return {}

        # Run the blocking database query in the recorder's executor
        states = await self._recorder.async_add_executor_job(self._get_states_sync, entity_id_list)

        # Extract first state for each entity (the start state)
        return {entity_id: states_list[0] for entity_id, states_list in states.items() if states_list}

    def _get_states_sync(self, entity_id_list: list[str]) -> dict[str, list[State]]:
        """Fetch states from the recorder synchronously.

        Run this in an executor to avoid blocking the event loop.
        """
        # get_significant_states handles session scope internally
        # With minimal_response=False (default), it returns full State objects
        result: dict[str, list[State | dict[str, Any]]] = recorder_history.get_significant_states(
            self._hass,
            start_time=self._timestamp,
            end_time=self._timestamp + timedelta(seconds=1),
            entity_ids=entity_id_list,
            include_start_time_state=True,
            significant_changes_only=False,  # include attribute-only changes
            no_attributes=False,  # preserve attributes (needed for forecasts)
        )
        # Cast since we're not using minimal_response, so we get full State objects
        return cast("dict[str, list[State]]", result)
