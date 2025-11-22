"""Utility functions for model elements."""

from collections.abc import Sequence
from typing import overload

import numpy as np


@overload
def broadcast_to_sequence(
    value: None,
    n_periods: int,
) -> None: ...


@overload
def broadcast_to_sequence(
    value: float | Sequence[float],
    n_periods: int,
) -> Sequence[float]: ...


def broadcast_to_sequence(
    value: float | Sequence[float] | None,
    n_periods: int,
) -> Sequence[float] | None:
    """Broadcast a scalar or sequence to match n_periods.

    Args:
        value: Scalar value, sequence to broadcast, or None
        n_periods: Target number of periods

    Returns:
        List of floats with length n_periods, or None if input is None

    """
    # Handle None input
    if value is None:
        return None

    # Convert to array and broadcast
    value_array = np.atleast_1d(value)

    if value_array.size == 0:
        msg = "Sequence cannot be empty"
        raise ValueError(msg)

    # If it's a single value, broadcast it
    if len(value_array) == 1:
        result: list[float] = np.broadcast_to(value_array, (n_periods,)).tolist()
        return result

    # If it's a sequence repeat the last value if it's not the same length
    if len(value_array) == n_periods:
        result = value_array.tolist()
        return result

    if len(value_array) > n_periods:
        result = value_array[:n_periods].tolist()
        return result

    result = value_array.tolist() + [float(value_array[-1])] * (n_periods - len(value_array))
    return result
