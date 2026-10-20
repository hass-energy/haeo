"""Read how much a meter rose since a point in time.

A meter is a running total, such as an energy sensor that only counts up.
Its state only says what it reads now, and many meters reset (an "energy
today" sensor returns to zero at midnight), so the reading alone cannot say
how much it rose since a window started. The integration reads the meter's
recorded totals, which carry on through resets, and injects them into the
meter's state as ``(time, total)`` pairs, the same way calendar events are
injected. Captured states keep the attribute, so diagnostics replay the same
totals.
"""

from collections.abc import Sequence
import math
from typing import Final

from custom_components.haeo.core.state import EntityState

# State attribute carrying a meter's recorded totals, injected by the integration
METER_TOTALS_ATTRIBUTE: Final = "haeo_meter_totals"

# A meter's running total at a time: (time, total), POSIX seconds
type MeterTotal = tuple[float, float]


def since_window_field(field_name: str) -> str:
    """Return the loaded config key holding how much a meter field rose since its window started."""
    return f"{field_name}_since_window"


def read_meter_totals(state: EntityState | None) -> list[MeterTotal] | None:
    """Return the totals injected into a meter's state, oldest first, or None when it carries none."""
    raw = state.attributes.get(METER_TOTALS_ATTRIBUTE) if state is not None else None
    if not isinstance(raw, Sequence) or isinstance(raw, str):
        return None
    totals: list[MeterTotal] = []
    for item in raw:
        if not isinstance(item, Sequence) or isinstance(item, str) or len(item) != 2:  # noqa: PLR2004 (a pair)
            return None
        at, total = item
        if isinstance(at, bool) or isinstance(total, bool) or not isinstance(at, (int, float)):
            return None
        if not isinstance(total, (int, float)) or not math.isfinite(total):
            return None
        totals.append((float(at), float(total)))
    return sorted(totals)


def rise_since(totals: Sequence[MeterTotal], since: float) -> float | None:
    """Return how much a meter rose from its total at *since* to its latest total.

    Returns None when no total is known at or before *since*, as when the
    window started before the recorded totals reach back. A meter whose
    totals fell, as a replaced meter's might, rose nothing.
    """
    before = [total for at, total in totals if at <= since]
    if not before:
        return None
    return max(totals[-1][1] - before[-1], 0.0)


__all__ = [
    "METER_TOTALS_ATTRIBUTE",
    "MeterTotal",
    "read_meter_totals",
    "rise_since",
    "since_window_field",
]
