"""Utility functions for model elements."""

from typing import overload

import numpy as np
from numpy.typing import NDArray


@overload
def broadcast_to_sequence(value: None, n_periods: int) -> None: ...


@overload
def broadcast_to_sequence(value: float | NDArray[np.float64], n_periods: int) -> NDArray[np.float64]: ...


def broadcast_to_sequence(
    value: float | NDArray[np.float64] | None,
    n_periods: int,
) -> NDArray[np.float64] | None:
    """Broadcast a scalar or sequence to match n_periods.

    For single values, broadcasts to n_periods length.
    For sequences that are too short, extends by repeating the last value.
    For sequences that are too long, truncates to n_periods.

    The result is always a new, writable float array, so whatever holds it can
    neither change the caller's array nor be changed through it.

    Args:
        value: Scalar value, array to broadcast, or None
        n_periods: Target number of periods

    Returns:
        Numpy array of floats with length n_periods, or None if input is None

    Raises:
        ValueError: If the input sequence is empty

    """
    if value is None:
        return None

    values = np.atleast_1d(np.asarray(value, dtype=np.float64))
    if values.size == 0:
        msg = "Sequence cannot be empty"
        raise ValueError(msg)

    result = np.empty(n_periods, dtype=np.float64)
    count = min(len(values), n_periods)
    result[:count] = values[:count]
    result[count:] = values[-1]
    return result
