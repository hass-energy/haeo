"""Type definitions and helpers for reactive infrastructure."""

from enum import Enum, auto

import numpy as np


class CachedKind(Enum):
    """Kind of cached method for reflection-based discovery."""

    CONSTRAINT = auto()
    COST = auto()


# Sentinel for unset values
class _UnsetType:
    """Sentinel type for unset parameter values."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "<UNSET>"


_UNSET = _UnsetType()

# Public alias for use in type hints and checks
UNSET: _UnsetType = _UNSET
"""Sentinel value indicating a TrackedParam has not been set.

Use `is_set()` to check if a parameter value has been set.
"""


def is_set(value: object) -> bool:
    """Check if a TrackedParam value has been set.

    Args:
        value: The value to check (from a TrackedParam access)

    Returns:
        True if the value is set (not UNSET), False otherwise

    Example:
        class MyElement(Element):
            capacity = TrackedParam[float]()

            @constraint
            def my_constraint(self) -> highs_linear_expression | None:
                if not is_set(self.capacity):
                    return None  # Skip constraint until capacity is set
                return self.energy <= self.capacity

    """
    return value is not _UNSET


def _values_equal(a: object, b: object) -> bool:
    """Compare two values for equality, handling numpy arrays."""
    # Handle numpy array comparisons
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        try:
            # Cast to ArrayLike to satisfy type checker
            return bool(np.array_equal(a, b))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return False
    # Standard equality for other types
    try:
        return bool(a == b)
    except (TypeError, ValueError):
        return False
