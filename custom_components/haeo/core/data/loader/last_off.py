"""When an availability source was last observed off.

An entity's state only says what it reports now. The integration looks up the
source's recent history and injects the end of its most recent off reading
into the state as the ``haeo_last_off`` attribute, the same way calendar
events are injected. Captured states keep the attribute, so diagnostics replay
the same value.
"""

from collections.abc import Sequence
from itertools import pairwise
from typing import Final

from custom_components.haeo.core.state import EntityState

from .extractors import parse_scalar_state

LAST_OFF_ATTRIBUTE: Final = "haeo_last_off"

# Readings below this count as off, matching how availability values are read.
_OFF_THRESHOLD: Final = 0.5


def last_off_field(field_name: str) -> str:
    """Return the loaded config key holding an availability field's last off time."""
    return f"{field_name}_last_off"


def is_off_state(raw: str) -> bool:
    """Return True when a state string reads as off ('off', 'false', or 0).

    States that do not parse as a number, such as 'unavailable' or 'unknown',
    are not off.
    """
    try:
        return parse_scalar_state(raw) < _OFF_THRESHOLD
    except ValueError:
        return False


def last_off_time(changes: Sequence[tuple[str, float]]) -> float | None:
    """Return when the most recent off reading ended.

    Args:
        changes: Chronological ``(state, changed_at)`` pairs, POSIX seconds.

    Returns:
        The time of the change that followed the latest off reading, or None
        when no off reading was followed by another state. Unparseable states
        never count as off, so a restart that briefly reads 'unavailable'
        between two on readings leaves no off time.

    """
    for (state, _changed_at), (_next_state, next_changed_at) in reversed(list(pairwise(changes))):
        if is_off_state(state):
            return next_changed_at
    return None


def read_last_off(state: EntityState | None) -> float | None:
    """Return the injected last off time from an entity state, if any."""
    if state is None:
        return None
    value = state.attributes.get(LAST_OFF_ATTRIBUTE)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


__all__ = ["LAST_OFF_ATTRIBUTE", "is_off_state", "last_off_field", "last_off_time", "read_last_off"]
