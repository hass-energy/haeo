"""Keep the on periods of an input's switches.

A switch, such as an appliance's running sensor, only says whether it is on
now. The calendar loader reads its recorded states once when it starts, then
extends them with the switch's state changes as they arrive. The on periods
are injected into the switch's state for the core loader, which reads when
the switch first switched on in a calendar window.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta
import logging
from typing import Final

from homeassistant.components.recorder import history as recorder_history
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.recorder import get_instance
from homeassistant.util import dt as dt_util

from custom_components.haeo.core.data.loader.switch import ON_PERIODS_ATTRIBUTE, OnPeriod, switch_state

_LOGGER = logging.getLogger(__name__)

RECORDER_DOMAIN: Final = "recorder"

# How far back the on periods reach, matching the meters' lookback
LOOKBACK: Final = timedelta(days=7)


class _OnPeriods:
    """One switch's on periods, extended with each new state."""

    def __init__(self) -> None:
        self._closed: list[OnPeriod] = []
        self._on_since: float | None = None

    @property
    def periods(self) -> list[OnPeriod]:
        """Return the on periods, oldest first, ending with the one still on."""
        return [*self._closed, (self._on_since, None)] if self._on_since is not None else list(self._closed)

    def record(self, state: State, at: float) -> None:
        """Start an on period when the switch turns on, and end it when it turns off."""
        on = switch_state(state.state)
        if on is True and self._on_since is None:
            self._on_since = at
        elif on is False and self._on_since is not None:
            self._closed.append((self._on_since, at))
            self._on_since = None
        cutoff = at - LOOKBACK.total_seconds()
        while self._closed and self._closed[0][1] is not None and self._closed[0][1] <= cutoff:
            self._closed.pop(0)


def _periods_from(states: Sequence[State]) -> _OnPeriods:
    """Return the on periods a switch's chronological states describe."""
    periods = _OnPeriods()
    for state in states:
        periods.record(state, state.last_changed_timestamp)
    return periods


class SwitchHistory:
    """On periods of an input's switches, kept current as they change."""

    def __init__(self, hass: HomeAssistant, entity_ids: Sequence[str]) -> None:
        """Initialize for the switches an input reads."""
        self._hass = hass
        self._entity_ids = list(entity_ids)
        self._switches: dict[str, _OnPeriods] = {}

    async def async_load(self) -> None:
        """Read each switch's recorded states over the lookback, then extend them with its live state."""
        recorded = await self._async_recorded(dt_util.utcnow() - LOOKBACK, None)
        self._switches = {entity_id: _periods_from(recorded.get(entity_id, [])) for entity_id in self._entity_ids}
        for entity_id in self._entity_ids:
            self.record(entity_id, self._hass.states.get(entity_id))

    def record(self, entity_id: str, state: State | None) -> None:
        """Extend a switch's on periods with its new state."""
        switch = self._switches.get(entity_id)
        if switch is not None and state is not None:
            switch.record(state, state.last_changed_timestamp)

    def attributes(self) -> dict[str, dict[str, object]]:
        """Return the on periods to inject into each switch's state."""
        return {entity_id: {ON_PERIODS_ATTRIBUTE: list(switch.periods)} for entity_id, switch in self._switches.items()}

    async def _async_recorded(self, start: datetime, end: datetime | None) -> dict[str, list[State]]:
        """Return each switch's recorded states from *start*, with the state it had then."""
        if not self._entity_ids or RECORDER_DOMAIN not in self._hass.config.components:
            return {}
        try:
            return await get_instance(self._hass).async_add_executor_job(
                _recorded_states, self._hass, self._entity_ids, start, end or dt_util.utcnow()
            )
        except Exception:
            _LOGGER.warning("Failed to read recorder history for %s", ", ".join(self._entity_ids), exc_info=True)
            return {}


def _recorded_states(
    hass: HomeAssistant, entity_ids: list[str], start: datetime, end: datetime
) -> dict[str, list[State]]:
    """Return the switches' recorded states between two times, each with the state it had at *start*.

    Runs in the recorder executor.
    """
    recorded: dict[str, list[State]] = {}
    for entity_id in entity_ids:
        recorded.update(
            recorder_history.state_changes_during_period(
                hass, start, end, entity_id, no_attributes=True, include_start_time_state=True
            )
        )
    return recorded


async def async_on_periods_at(hass: HomeAssistant, entity_id: str, at: datetime) -> list[OnPeriod] | None:
    """Return a switch's on periods over the lookback ending at a past time.

    Historical diagnostics inject these into the switch's recorded state, as a
    live run injects its current periods. Returns None when the history
    cannot be read, so the switch carries no periods rather than wrong ones.
    """
    try:
        recorded = await get_instance(hass).async_add_executor_job(
            _recorded_states, hass, [entity_id], at - LOOKBACK, at
        )
    except Exception:
        _LOGGER.warning("Failed to read recorder history for %s", entity_id, exc_info=True)
        return None
    return _periods_from(recorded.get(entity_id, [])).periods


__all__ = ["LOOKBACK", "SwitchHistory", "async_on_periods_at"]
