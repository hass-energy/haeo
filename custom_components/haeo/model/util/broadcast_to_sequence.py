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
) -> list[float]: ...


def broadcast_to_sequence(
    value: float | Sequence[float] | None,
    n_periods: int,
) -> list[float] | None:
    """Broadcast a scalar or sequence to match n_periods.

    Args:
        value: Scalar value, sequence to broadcast, or None
        n_periods: Target number of periods

    Returns:
        List of floats with length n_periods, or None if input is None

    Raises:
        ValueError: If sequence length doesn't match n_periods

    """
    # Handle None input
    if value is None:
        return None

    # Convert to array and broadcast
    value_array = np.atleast_1d(value)

    # If it's a single value, broadcast it
    if len(value_array) == 1:
        result: list[float] = np.broadcast_to(value_array, (n_periods,)).tolist()
        return result

    # If it's a sequence, validate length
    if len(value_array) != n_periods:
        msg = f"Sequence length ({len(value_array)}) must match n_periods ({n_periods})"
        raise ValueError(msg)

    result_list: list[float] = value_array.tolist()
    return result_list
