"""Look up a source's last recorded reading, for a source with no reading when HAEO starts.

Input stores keep a source's last reading only in memory, so after a restart
a source that comes up without a reading would have nothing to hold. Its last
state with a reading in the recorder stands in for it.
"""

import asyncio
import logging
from typing import Final

from homeassistant.components.recorder import history
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.recorder import get_instance

from custom_components.haeo.core.state import NO_READING_STATES
from custom_components.haeo.inputs.meter_history import RECORDER_DOMAIN, RECORDER_READ_TIMEOUT

_LOGGER = logging.getLogger(__name__)

# How many of a source's latest recorded states are searched for one with a reading
RECORDED_STATES: Final = 10


async def async_last_recorded_reading(hass: HomeAssistant, entity_id: str) -> State | None:
    """Return a source's latest recorded state with a reading, or None when there is none or it cannot be read.

    Waits at most ``RECORDER_READ_TIMEOUT``, so a slow recorder does not hold
    up loading.
    """
    if RECORDER_DOMAIN not in hass.config.components:
        return None
    try:
        async with asyncio.timeout(RECORDER_READ_TIMEOUT):
            return await get_instance(hass).async_add_executor_job(last_recorded_reading, hass, entity_id)
    except Exception:
        _LOGGER.warning("Failed to read the last recorded state of %s", entity_id, exc_info=True)
        return None


def last_recorded_reading(hass: HomeAssistant, entity_id: str) -> State | None:
    """Return the latest of a source's last recorded states that has a reading. Runs in the recorder executor."""
    states = history.get_last_state_changes(hass, RECORDED_STATES, entity_id).get(entity_id, [])
    return next((state for state in reversed(states) if state.state not in NO_READING_STATES), None)


__all__ = ["RECORDED_STATES", "async_last_recorded_reading", "last_recorded_reading"]
