"""Keep the recent history of an input's source entities.

Some inputs need their source's recent past as well as its current state:
an EV's plugged-in sensor needs the periods it read unplugged, and its
odometer needs its readings. The recorder holds that history. Each input
reads it once when it starts, then appends its sources' state changes as
they arrive, so the recorder is not queried again while the input runs.
The core history module turns the changes into the attributes injected
into the source states.

The lookup is best effort. Without the recorder, without history for an
entity (excluded from recording, or nothing inside the lookback), or when
the query fails, the entity keeps only the changes seen since the input
started.
"""

import asyncio
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
import logging
from typing import Final

from homeassistant.components.recorder import history
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.recorder import get_instance
from homeassistant.util import dt as dt_util

from custom_components.haeo.core.data.loader.source_history import history_attributes
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.state import EntityState, StateMachine
from custom_components.haeo.ha_state_machine import AnnotatedState

_LOGGER = logging.getLogger(__name__)

RECORDER_DOMAIN: Final = "recorder"

# How far back history reaches. A week covers multi-day trips; older changes
# are dropped.
LOOKBACK: Final = timedelta(days=7)


class SourceHistory:
    """Recorded state changes of an input's source entities, kept current as they change."""

    def __init__(self, hass: HomeAssistant, entity_ids: Sequence[str], output_type: OutputType) -> None:
        """Initialize for the source entities of an input of *output_type*."""
        self._hass = hass
        self._entity_ids = list(entity_ids)
        self._output_type = output_type
        self._changes: dict[str, list[tuple[str, float]]] = {entity_id: [] for entity_id in entity_ids}

    async def async_load(self) -> None:
        """Read each source's changes over the lookback from the recorder, with its live state."""
        found = await asyncio.gather(*(self._async_recorded(entity_id) for entity_id in self._entity_ids))
        self._changes = dict(zip(self._entity_ids, found, strict=True))
        for entity_id in self._entity_ids:
            self.record(entity_id, self._hass.states.get(entity_id))

    def record(self, entity_id: str, state: State | None) -> None:
        """Append a source's new state when its value changed, dropping changes older than the lookback.

        The recorder commits in batches, so a live state can be newer than
        the last recorded change.
        """
        if state is None:
            return
        changes = self._changes.setdefault(entity_id, [])
        if not changes or state.last_changed_timestamp > changes[-1][1]:
            changes.append((state.state, state.last_changed_timestamp))
        cutoff = (dt_util.utcnow() - LOOKBACK).timestamp()
        while len(changes) > 1 and changes[1][1] <= cutoff:
            changes.pop(0)
        if changes and changes[0][1] < cutoff:
            changes[0] = (changes[0][0], cutoff)

    def attributes(self) -> dict[str, dict[str, object]]:
        """Return the history attributes to inject into each source's state."""
        result: dict[str, dict[str, object]] = {}
        for entity_id, changes in self._changes.items():
            attributes = history_attributes(self._output_type, changes)
            if attributes is not None:
                result[entity_id] = attributes
        return result

    async def _async_recorded(self, entity_id: str) -> list[tuple[str, float]]:
        """Return the entity's recorded changes over the lookback, oldest first."""
        if RECORDER_DOMAIN not in self._hass.config.components:
            return []
        start = dt_util.utcnow() - LOOKBACK
        try:
            states = await get_instance(self._hass).async_add_executor_job(_state_changes, self._hass, start, entity_id)
        except Exception:
            _LOGGER.warning("Failed to read recorder history for %s", entity_id, exc_info=True)
            return []
        return [(state.state, state.last_changed_timestamp) for state in states]


class HistoryStateMachine(StateMachine):
    """State machine decorator that injects history attributes into source states."""

    def __init__(self, base: StateMachine, attributes: Mapping[str, Mapping[str, object]]) -> None:
        """Initialize with a base state machine and per-entity history attributes."""
        self._base = base
        self._attributes = attributes

    def get(self, entity_id: str) -> EntityState | None:
        """Return the entity state, with its history attributes merged when known."""
        state = self._base.get(entity_id)
        extra = self._attributes.get(entity_id)
        if state is None or extra is None:
            return state
        return AnnotatedState(state, extra)


def _state_changes(hass: HomeAssistant, start: datetime, entity_id: str) -> list[State]:
    """Return the entity's state changes since *start*, oldest first.

    Runs in the recorder executor.
    """
    return history.state_changes_during_period(
        hass,
        start,
        entity_id=entity_id,
        no_attributes=True,
        include_start_time_state=True,
    ).get(entity_id, [])


__all__ = ["LOOKBACK", "HistoryStateMachine", "SourceHistory"]
