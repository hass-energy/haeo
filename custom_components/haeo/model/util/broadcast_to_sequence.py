"""Utility functions for model elements."""

from collections.abc import Sequence
from typing import overload

import numpy as np
from numpy.typing import NDArray


@overload
def broadcast_to_sequence(value: None, n_periods: int) -> None: ...


@overload
def broadcast_to_sequence(value: float | Sequence[float], n_periods: int) -> NDArray[np.float64]: ...


def broadcast_to_sequence(value: float | Sequence[float] | None, n_periods: int) -> NDArray[np.float64] | None:
    """Broadcast a scalar or sequence to match n_periods.

    For single values, broadcasts to n_periods length.
    For sequences that are too short, extends by repeating the last value.
    For sequences that are too long, truncates to n_periods.

    Args:
        value: Scalar value, sequence to broadcast, or None
        n_periods: Target number of periods

    Returns:
        Numpy array of floats with length n_periods, or None if input is None

    Raises:
        ValueError: If the input sequence is empty

    """
    # Handle None input
    if value is None:
        return None

    # Convert to array and broadcast
    value_array: NDArray[np.float64] = np.atleast_1d(value)

    if value_array.size == 0:
        msg = "Sequence cannot be empty"
        raise ValueError(msg)

    # If it's a single value, broadcast it
    if len(value_array) == 1:
        return np.broadcast_to(value_array, (n_periods,))

    # If it's a sequence repeat the last value if it's not the same length
    if len(value_array) == n_periods:
        return value_array

    if len(value_array) > n_periods:
        return value_array[:n_periods]

    # Extend by repeating the last value
    extended = np.empty(n_periods, dtype=np.float64)
    extended[: len(value_array)] = value_array
    extended[len(value_array) :] = value_array[-1]
    return extended
