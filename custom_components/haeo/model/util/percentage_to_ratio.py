"""Utility function to convert percentages to ratios."""

from typing import Any, overload

import numpy as np
from numpy.typing import NDArray


@overload
def percentage_to_ratio(value: None) -> None: ...


@overload
def percentage_to_ratio(value: float | NDArray[np.floating[Any]]) -> NDArray[np.float64]: ...


def percentage_to_ratio(
    value: float | NDArray[np.floating[Any]] | None,
) -> NDArray[np.float64] | None:
    """Convert percentage (0-100) to ratio (0-1).

    Args:
        value: Percentage value, array of percentages, or None

    Returns:
        Array of ratios (0-1), or None if input is None

    """
    if value is None:
        return None

    if isinstance(value, np.ndarray):
        return value.astype(float) / 100.0

    return np.array([value / 100.0], dtype=float)
