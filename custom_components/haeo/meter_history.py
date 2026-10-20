"""Keep the running totals of an input's meters, through resets.

A meter, such as an energy sensor that only counts up, can reset: an
"energy today" sensor returns to zero at midnight. The recorder's statistics
keep a sum for such sensors that carries on through resets, as the Energy
dashboard reads it. Each meter input reads that sum from the 5-minute
statistics once when it starts, then extends it with the meter's state
changes as they arrive, treating a fall in the reading as a reset. The totals
are injected into the meter's state for the core loader, which reads how
much the meter rose since a window started.

Statistics only exist for sensors with a total or total_increasing state
class, which is why meter fields only offer those sensors. A meter without
statistics, or a lookup that fails, keeps only the changes seen since the
input started, so a window that began earlier is credited nothing.
"""

import asyncio
from collections.abc import Sequence
from datetime import datetime, timedelta
import logging
from typing import Final

from homeassistant.components.recorder import statistics
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.recorder import get_instance
from homeassistant.util import dt as dt_util

from custom_components.haeo.core.data.loader.meter import METER_TOTALS_ATTRIBUTE, MeterTotal

_LOGGER = logging.getLogger(__name__)

RECORDER_DOMAIN: Final = "recorder"

# How far back the totals reach. Short-term statistics are kept for ten days
# by default, which a week stays inside; a window that began earlier is
# credited nothing.
LOOKBACK: Final = timedelta(days=7)


def _reading(state: State | None) -> float | None:
    """Return a meter state's numeric reading, or None when it reads no number."""
    if state is None:
        return None
    try:
        return float(state.state)
    except ValueError:
        return None


class _MeterTotals:
    """One meter's running totals, extended with each new reading."""

    def __init__(self, totals: list[MeterTotal], last_reading: float | None) -> None:
        self.totals = totals
        self._last_reading = last_reading

    def record(self, reading: float, at: float) -> None:
        """Add a reading's rise to the total; a reading below the last is a reset that rose from zero."""
        if self._last_reading is not None:
            rise = reading - self._last_reading if reading >= self._last_reading else reading
            last_total = self.totals[-1][1] if self.totals else 0.0
            self.totals.append((at, last_total + rise))
        elif not self.totals:
            self.totals.append((at, 0.0))
        self._last_reading = reading
        cutoff = at - LOOKBACK.total_seconds()
        while len(self.totals) > 1 and self.totals[1][0] <= cutoff:
            self.totals.pop(0)


class MeterHistory:
    """Running totals of an input's meters, kept current as they change."""

    def __init__(self, hass: HomeAssistant, entity_ids: Sequence[str]) -> None:
        """Initialize for the meters an input reads."""
        self._hass = hass
        self._entity_ids = list(entity_ids)
        self._meters: dict[str, _MeterTotals] = {}

    async def async_load(self) -> None:
        """Read each meter's recorded totals over the lookback, then extend them with its live state."""
        found = await asyncio.gather(*(self._async_recorded(entity_id) for entity_id in self._entity_ids))
        self._meters = {
            entity_id: _MeterTotals(totals, last_reading)
            for entity_id, (totals, last_reading) in zip(self._entity_ids, found, strict=True)
        }
        for entity_id in self._entity_ids:
            self.record(entity_id, self._hass.states.get(entity_id))

    def record(self, entity_id: str, state: State | None) -> None:
        """Extend a meter's totals with its new state, when it reads a number."""
        reading = _reading(state)
        meter = self._meters.get(entity_id)
        if reading is not None and meter is not None and state is not None:
            meter.record(reading, state.last_updated_timestamp)

    def attributes(self) -> dict[str, dict[str, object]]:
        """Return the totals to inject into each meter's state."""
        return {entity_id: {METER_TOTALS_ATTRIBUTE: list(meter.totals)} for entity_id, meter in self._meters.items()}

    async def _async_recorded(self, entity_id: str) -> tuple[list[MeterTotal], float | None]:
        """Return a meter's recorded totals over the lookback and its last recorded reading."""
        if RECORDER_DOMAIN not in self._hass.config.components:
            return [], None
        start = dt_util.utcnow() - LOOKBACK
        try:
            return await get_instance(self._hass).async_add_executor_job(
                recorded_totals, self._hass, entity_id, start, None
            )
        except Exception:
            _LOGGER.warning("Failed to read recorder statistics for %s", entity_id, exc_info=True)
            return [], None


async def async_meter_totals_at(hass: HomeAssistant, entity_id: str, at: datetime, state: State) -> list[MeterTotal]:
    """Return a meter's running totals over the lookback ending at a past time, with its state then.

    Historical diagnostics inject these into the meter's recorded state, as a
    live run injects its current totals.
    """
    totals, last_reading = await get_instance(hass).async_add_executor_job(
        recorded_totals, hass, entity_id, at - LOOKBACK, at
    )
    meter = _MeterTotals(totals, last_reading)
    reading = _reading(state)
    if reading is not None:
        meter.record(reading, at.timestamp())
    return meter.totals


def recorded_totals(
    hass: HomeAssistant, entity_id: str, start: datetime, end: datetime | None
) -> tuple[list[MeterTotal], float | None]:
    """Return a meter's 5-minute statistics totals between two times, and its last reading.

    Each total is the statistics sum at the end of its 5-minute bucket, which
    carries on through resets. Runs in the recorder executor.
    """
    rows = statistics.statistics_during_period(hass, start, end, {entity_id}, "5minute", None, {"sum", "state"}).get(
        entity_id, []
    )
    totals = [
        (ended, total)
        for row in rows
        if (ended := row.get("end")) is not None and (total := row.get("sum")) is not None
    ]
    readings = [reading for row in rows if (reading := row.get("state")) is not None]
    return totals, readings[-1] if readings else None


__all__ = ["LOOKBACK", "MeterHistory", "async_meter_totals_at", "recorded_totals"]
