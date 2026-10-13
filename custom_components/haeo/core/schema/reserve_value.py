"""Schema values for inputs derived from the network's backup energy reserve."""

from __future__ import annotations

from collections.abc import Mapping
from numbers import Real
from typing import Literal, TypedDict, TypeGuard

VALUE_TYPE_RESERVE = "reserve"


class ReserveValue(TypedDict):
    """Schema value representing a reserve derived from the network's loads and generation.

    The ``value`` field is the window in hours the reserve must cover.
    """

    type: Literal["reserve"]
    value: float


def as_reserve_value(window_hours: float) -> ReserveValue:
    """Create a reserve schema value from a window length in hours."""
    return {"type": VALUE_TYPE_RESERVE, "value": float(window_hours)}


def is_reserve_value(value: object) -> TypeGuard[ReserveValue]:
    """Return True if value is a reserve schema value."""
    if not isinstance(value, Mapping):
        return False
    if value.get("type") != VALUE_TYPE_RESERVE:
        return False
    window = value.get("value")
    return isinstance(window, Real)


__all__ = [
    "VALUE_TYPE_RESERVE",
    "ReserveValue",
    "as_reserve_value",
    "is_reserve_value",
]
