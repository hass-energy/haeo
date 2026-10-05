"""Look up when availability sources were last off from the recorder.

An availability input (such as an EV's plugged-in sensor) only reports what
its source says now. The recorder keeps the source's recent history, so each
load queries it for the end of the latest off reading and injects that into
the source state as the core last off attribute. Nothing is stored between
loads: every load asks the recorder again.

The lookup is best effort. Without the recorder, without history for the
entity (excluded from recording, or no off reading inside the lookback), or
when the query fails, the state is left as it is and the input loads with no
last off time.
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

from custom_components.haeo.core.data.loader.last_off import LAST_OFF_ATTRIBUTE, last_off_time
from custom_components.haeo.core.state import EntityState, StateMachine
from custom_components.haeo.ha_state_machine import AnnotatedState

_LOGGER = logging.getLogger(__name__)

RECORDER_DOMAIN: Final = "recorder"

# How far back to look for an off reading. A week covers multi-day trips while
# keeping the query to a handful of rows for a plug sensor; an off reading
# older than this loads as no last off time.
LOOKBACK: Final = timedelta(days=7)


class LastOffStateMachine(StateMachine):
    """State machine decorator that injects last off times into source states."""

    def __init__(self, base: StateMachine, last_off: Mapping[str, float]) -> None:
        """Initialize with a base state machine and per-entity last off times."""
        self._base = base
        self._last_off = last_off

    def get(self, entity_id: str) -> EntityState | None:
        """Return the entity state, with its last off time merged when known."""
        state = self._base.get(entity_id)
        last_off = self._last_off.get(entity_id)
        if state is None or last_off is None:
            return state
        return AnnotatedState(state, {LAST_OFF_ATTRIBUTE: last_off})


async def async_last_off_state_machine(
    hass: HomeAssistant,
    base: StateMachine,
    entity_ids: Sequence[str],
) -> LastOffStateMachine:
    """Look up each entity's last off time and wrap *base* to inject them."""
    found = await asyncio.gather(*(async_last_off(hass, entity_id) for entity_id in entity_ids))
    last_off = {entity_id: value for entity_id, value in zip(entity_ids, found, strict=True) if value is not None}
    return LastOffStateMachine(base, last_off)


async def async_last_off(hass: HomeAssistant, entity_id: str) -> float | None:
    """Return when *entity_id* last stopped reading off, or None when unknown."""
    if RECORDER_DOMAIN not in hass.config.components:
        return None

    start = dt_util.utcnow() - LOOKBACK
    try:
        states = await get_instance(hass).async_add_executor_job(_state_changes, hass, start, entity_id)
    except Exception:
        _LOGGER.warning("Failed to read recorder history for %s", entity_id, exc_info=True)
        return None

    changes = [(state.state, state.last_changed_timestamp) for state in states]
    # The recorder commits in batches, so the live state can be newer than
    # the last recorded change; it is what ends an off reading just now.
    live = hass.states.get(entity_id)
    if live is not None and (not changes or live.last_changed_timestamp > changes[-1][1]):
        changes.append((live.state, live.last_changed_timestamp))
    return last_off_time(changes)


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


__all__ = ["LOOKBACK", "LastOffStateMachine", "async_last_off", "async_last_off_state_machine"]
