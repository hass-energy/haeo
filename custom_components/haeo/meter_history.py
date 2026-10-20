"""Keep the running totals of an input's meters, through resets.

A meter, such as an energy sensor that only counts up, can reset: an
"energy today" sensor returns to zero at midnight. The recorder's statistics
keep a sum for such sensors that carries on through resets, as the Energy
dashboard reads it. The calendar loader reads that sum from the 5-minute
statistics once when it starts, then extends it with the meter's state
changes as they arrive, detecting resets as the recorder does. The totals
are injected into the meter's state for the core loader, which reads how
much the meter rose since a window started.

Statistics only exist for sensors with a total or total_increasing state
class, which is why meter fields only offer those sensors. A meter without
statistics, or a lookup that fails, keeps only the changes seen since the
loader started, so a window that began earlier is credited only those.
"""

import asyncio
from collections.abc import Sequence
from datetime import datetime, timedelta
import logging
from typing import Final

from homeassistant.components.recorder import statistics
from homeassistant.components.sensor import ATTR_LAST_RESET, ATTR_STATE_CLASS, SensorStateClass
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.recorder import get_instance
from homeassistant.util import dt as dt_util

from custom_components.haeo.core.data.loader.meter import METER_TOTALS_ATTRIBUTE, MeterTotal

_LOGGER = logging.getLogger(__name__)

RECORDER_DOMAIN: Final = "recorder"

# How far back the totals reach. Short-term statistics are kept for ten days
# by default, which a week stays inside; a window that began earlier is
# credited from the earliest total.
LOOKBACK: Final = timedelta(days=7)

# The spacing kept between live totals, matching the statistics' 5-minute
# buckets, so a meter that updates every few seconds keeps a bounded history.
SPACING: Final = timedelta(minutes=5)

# A total_increasing reading below this share of the last one is a reset, as
# the recorder decides; a smaller dip is noise that the next reading undoes.
RESET_RATIO: Final = 0.9


def _unit(state: State | None) -> str | None:
    """Return a meter state's unit of measurement, or None when it states none."""
    unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) if state is not None else None
    return unit if isinstance(unit, str) else None


def _carries_totals(state: State | None) -> bool:
    """Return True when a meter's state already carries its running totals."""
    return state is not None and METER_TOTALS_ATTRIBUTE in state.attributes


def _reading(state: State | None) -> float | None:
    """Return a meter state's numeric reading, or None when it reads no number."""
    if state is None:
        return None
    try:
        return float(state.state)
    except ValueError:
        return None


def _is_reset(state: State, reading: float, last: State | None, last_reading: float) -> bool:
    """Return whether a meter reset between two readings, as the recorder decides.

    A total meter resets when its last_reset changes. A total_increasing meter
    resets when its reading falls below most of the last one.
    """
    if state.attributes.get(ATTR_STATE_CLASS) == SensorStateClass.TOTAL_INCREASING:
        return reading < RESET_RATIO * last_reading
    last_reset = state.attributes.get(ATTR_LAST_RESET)
    return last is not None and last_reset is not None and last_reset != last.attributes.get(ATTR_LAST_RESET)


class _MeterTotals:
    """One meter's running totals, extended with each new reading.

    Totals are kept at least ``SPACING`` apart, with the latest held aside
    until the next one is far enough from the last kept, so the history stays
    bounded however often the meter updates.
    """

    def __init__(self, totals: list[MeterTotal], last_reading: float | None) -> None:
        self._kept = totals
        self._latest: MeterTotal | None = None
        self._last_reading = last_reading
        self._last_state: State | None = None

    @property
    def totals(self) -> list[MeterTotal]:
        """Return the totals, oldest first, ending with the latest."""
        return [*self._kept, self._latest] if self._latest is not None else list(self._kept)

    def record(self, state: State, reading: float, at: float) -> None:
        """Add a reading's rise to the total; after a reset the meter rose from zero."""
        if self._last_reading is None:
            if not self._kept and self._latest is None:
                self._latest = (at, 0.0)
        else:
            reset = _is_reset(state, reading, self._last_state, self._last_reading)
            rise = reading if reset else reading - self._last_reading
            totals = self.totals
            last_total = totals[-1][1] if totals else 0.0
            if self._latest is not None and (
                not self._kept or self._latest[0] - self._kept[-1][0] >= SPACING.total_seconds()
            ):
                self._kept.append(self._latest)
            self._latest = (at, last_total + rise)
        self._last_reading = reading
        self._last_state = state
        cutoff = at - LOOKBACK.total_seconds()
        while len(self._kept) > 1 and self._kept[1][0] <= cutoff:
            self._kept.pop(0)


class MeterHistory:
    """Running totals of an input's meters, kept current as they change."""

    def __init__(self, hass: HomeAssistant, entity_ids: Sequence[str]) -> None:
        """Initialize for the meters an input reads."""
        self._hass = hass
        self._entity_ids = list(entity_ids)
        self._meters: dict[str, _MeterTotals] = {}

    async def async_load(self) -> None:
        """Read each meter's recorded totals over the lookback, then extend them with its live state."""
        found = await asyncio.gather(
            *(self._async_recorded(entity_id, self._hass.states.get(entity_id)) for entity_id in self._entity_ids)
        )
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
            meter.record(state, reading, state.last_updated_timestamp)

    def attributes(self) -> dict[str, dict[str, object]]:
        """Return the totals to inject into each meter's state.

        A meter whose state already carries totals, as a replayed diagnostics
        or scenario state does, keeps them, as a calendar keeps its events.
        """
        return {
            entity_id: {METER_TOTALS_ATTRIBUTE: list(meter.totals)}
            for entity_id, meter in self._meters.items()
            if not _carries_totals(self._hass.states.get(entity_id))
        }

    async def _async_recorded(self, entity_id: str, state: State | None) -> tuple[list[MeterTotal], float | None]:
        """Return a meter's recorded totals over the lookback and its last recorded reading."""
        if RECORDER_DOMAIN not in self._hass.config.components:
            return [], None
        start = dt_util.utcnow() - LOOKBACK
        try:
            return await get_instance(self._hass).async_add_executor_job(
                recorded_totals, self._hass, entity_id, _unit(state), start, None
            )
        except Exception:
            _LOGGER.warning("Failed to read recorder statistics for %s", entity_id, exc_info=True)
            return [], None


async def async_meter_totals_at(
    hass: HomeAssistant, entity_id: str, at: datetime, state: State
) -> list[MeterTotal] | None:
    """Return a meter's running totals over the lookback ending at a past time, with its state then.

    Historical diagnostics inject these into the meter's recorded state, as a
    live run injects its current totals. Returns None when the statistics
    cannot be read, so the meter carries no totals rather than wrong ones.
    """
    try:
        totals, last_reading = await get_instance(hass).async_add_executor_job(
            recorded_totals, hass, entity_id, _unit(state), at - LOOKBACK, at
        )
    except Exception:
        _LOGGER.warning("Failed to read recorder statistics for %s", entity_id, exc_info=True)
        return None
    meter = _MeterTotals(totals, last_reading)
    reading = _reading(state)
    if reading is not None:
        meter.record(state, reading, at.timestamp())
    return meter.totals


def recorded_totals(
    hass: HomeAssistant, entity_id: str, unit: str | None, start: datetime, end: datetime | None
) -> tuple[list[MeterTotal], float | None]:
    """Return a meter's 5-minute statistics totals between two times, and its last reading.

    Each total is the statistics sum at the end of its 5-minute bucket, which
    carries on through resets. Values are converted to the meter's current
    unit, which its live readings are in. Only buckets ending by *end* count,
    so no reading from after it is seen. Runs in the recorder executor.
    """
    converter = statistics.STATISTIC_UNIT_TO_UNIT_CONVERTER.get(unit)
    units = {converter.UNIT_CLASS: unit} if converter is not None and unit is not None else None
    rows = statistics.statistics_during_period(hass, start, end, {entity_id}, "5minute", units, {"sum", "state"}).get(
        entity_id, []
    )
    if end is not None:
        rows = [row for row in rows if (ended := row.get("end")) is not None and ended <= end.timestamp()]
    totals = [
        (ended, total)
        for row in rows
        if (ended := row.get("end")) is not None and (total := row.get("sum")) is not None
    ]
    readings = [reading for row in rows if (reading := row.get("state")) is not None]
    return totals, readings[-1] if readings else None


__all__ = ["LOOKBACK", "SPACING", "MeterHistory", "async_meter_totals_at", "recorded_totals"]
