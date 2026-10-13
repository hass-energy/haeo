"""Validation for parameters that must never be negative."""

import numpy as np
from numpy.typing import NDArray


def require_non_negative(name: str, value: float | NDArray[np.float64]) -> None:
    """Raise if any entry of a parameter is negative.

    Slack prices must be non-negative: a negative price rewards booking the
    slack up to its bound without the priced event actually happening.

    Args:
        name: Parameter name used in the error message
        value: Scalar or array value to check

    Raises:
        ValueError: If any entry is negative

    """
    if np.any(np.asarray(value) < 0.0):
        msg = f"{name} must be non-negative"
        raise ValueError(msg)
