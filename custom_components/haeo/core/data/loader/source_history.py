"""Recent history of an input's source entities.

An entity's state only says what it reports now. For some inputs the recent
past matters too: when an EV's plugged-in sensor was unplugged, and what its
odometer read at that moment. The integration reads the source's recorded
state changes and injects them into the source state as an attribute, the
same way calendar events are injected. Captured states keep the attribute,
so diagnostics replay the same history.

Which history an input gets follows from its output type: an availability
input gets the periods its source read off, and a distance input gets its
source's readings.
"""

from collections.abc import Sequence
import math
from typing import Final

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.state import EntityState

from .extractors import parse_scalar_state

OFF_PERIODS_ATTRIBUTE: Final = "haeo_off_periods"
READINGS_ATTRIBUTE: Final = "haeo_readings"

# Readings below this count as off, matching how availability values are read.
_OFF_THRESHOLD: Final = 0.5

# A period the source read off: (start, end), POSIX seconds, end None while still off.
type OffPeriod = tuple[float, float | None]

# A recorded value: (changed_at, value), POSIX seconds.
type Reading = tuple[float, float]


def off_periods_field(field_name: str) -> str:
    """Return the loaded config key holding an availability field's off periods."""
    return f"{field_name}_off_periods"


def readings_field(field_name: str) -> str:
    """Return the loaded config key holding a distance field's recorded readings."""
    return f"{field_name}_readings"


def _parsed(raw: str) -> float | None:
    try:
        value = parse_scalar_state(raw)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def is_off_state(raw: str) -> bool:
    """Return True when a state string reads as off ('off', 'false', or 0).

    States that do not parse as a number, such as 'unavailable' or 'unknown',
    are not off.
    """
    value = _parsed(raw)
    return value is not None and value < _OFF_THRESHOLD


def is_on_state(raw: str) -> bool:
    """Return True when a state string reads as on ('on', 'true', or 1).

    States that do not parse as a number, such as 'unavailable' or 'unknown',
    are not on.
    """
    value = _parsed(raw)
    return value is not None and value >= _OFF_THRESHOLD


def off_periods(changes: Sequence[tuple[str, float]]) -> list[OffPeriod]:
    """Return the periods a source read off, oldest first.

    Args:
        changes: Chronological ``(state, changed_at)`` pairs, POSIX seconds.

    An off period runs from the first off reading to the next on reading.
    Unparseable states neither start nor end one, so an unplugged car whose
    integration reads 'unavailable' for a while stays off until it reads on,
    and a restart that briefly reads 'unavailable' while plugged in is not an
    unplug.

    """
    periods: list[OffPeriod] = []
    start: float | None = None
    for state, changed_at in changes:
        if is_off_state(state):
            if start is None:
                start = changed_at
        elif is_on_state(state) and start is not None:
            periods.append((start, changed_at))
            start = None
    if start is not None:
        periods.append((start, None))
    return periods


def readings(changes: Sequence[tuple[str, float]]) -> list[Reading]:
    """Return the numeric readings among a source's state changes, oldest first."""
    return [(changed_at, value) for state, changed_at in changes if (value := _parsed(state)) is not None]


def takes_history(output_type: OutputType) -> bool:
    """Return True when an input of *output_type* uses its sources' recent history."""
    return output_type in (OutputType.AVAILABILITY, OutputType.DISTANCE)


def history_attributes(output_type: OutputType, changes: Sequence[tuple[str, float]]) -> dict[str, object] | None:
    """Return the history attributes to inject for an input of *output_type*, or None if it takes none."""
    if output_type is OutputType.AVAILABILITY:
        return {OFF_PERIODS_ATTRIBUTE: off_periods(changes)}
    if output_type is OutputType.DISTANCE:
        return {READINGS_ATTRIBUTE: readings(changes)}
    return None


def _pairs(state: EntityState | None, attribute: str) -> list[tuple[object, object]] | None:
    """Return an injected attribute as a list of pairs, or None when absent or malformed."""
    if state is None:
        return None
    raw = state.attributes.get(attribute)
    if not isinstance(raw, Sequence) or isinstance(raw, str):
        return None
    pairs: list[tuple[object, object]] = []
    for item in raw:
        if not isinstance(item, Sequence) or isinstance(item, str) or len(item) != 2:  # noqa: PLR2004 (a pair)
            return None
        pairs.append((item[0], item[1]))
    return pairs


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def read_off_periods(state: EntityState | None) -> list[OffPeriod] | None:
    """Return the injected off periods from an entity state, or None when it carries none."""
    pairs = _pairs(state, OFF_PERIODS_ATTRIBUTE)
    if pairs is None:
        return None
    periods: list[OffPeriod] = []
    for raw_start, raw_end in pairs:
        start = _number(raw_start)
        end = None if raw_end is None else _number(raw_end)
        if start is None or (raw_end is not None and end is None):
            return None
        periods.append((start, end))
    return periods


def read_readings(state: EntityState | None) -> list[Reading] | None:
    """Return the injected readings from an entity state, or None when it carries none."""
    pairs = _pairs(state, READINGS_ATTRIBUTE)
    if pairs is None:
        return None
    result: list[Reading] = []
    for raw_time, raw_value in pairs:
        changed_at = _number(raw_time)
        value = _number(raw_value)
        if changed_at is None or value is None:
            return None
        result.append((changed_at, value))
    return result


def all_off(per_source: Sequence[Sequence[OffPeriod]]) -> list[OffPeriod]:
    """Return the periods every source read off at once.

    Several plugged-in sensors read plugged in while any of them does, so the
    car was unplugged only while all of them were off.
    """
    if not per_source:
        return []
    combined = list(per_source[0])
    for periods in per_source[1:]:
        combined = _intersect(combined, periods)
    return combined


def _intersect(a: Sequence[OffPeriod], b: Sequence[OffPeriod]) -> list[OffPeriod]:
    result: list[OffPeriod] = []
    for a_start, a_end in a:
        for b_start, b_end in b:
            start = max(a_start, b_start)
            ends = [end for end in (a_end, b_end) if end is not None]
            end = min(ends) if ends else None
            if end is None or end > start:
                result.append((start, end))
    return sorted(result)


def value_at(history: Sequence[Reading], at: float) -> float | None:
    """Return the latest reading at or before *at*, or None when there is none."""
    value: float | None = None
    for changed_at, reading in history:
        if changed_at > at:
            break
        value = reading
    return value


__all__ = [
    "OFF_PERIODS_ATTRIBUTE",
    "READINGS_ATTRIBUTE",
    "OffPeriod",
    "Reading",
    "all_off",
    "history_attributes",
    "is_off_state",
    "is_on_state",
    "off_periods",
    "off_periods_field",
    "read_off_periods",
    "read_readings",
    "readings",
    "readings_field",
    "takes_history",
    "value_at",
]
