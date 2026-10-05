"""Clean values resolved from source entities before they reach the optimizer."""

from typing import Any, Final

import numpy as np
from numpy.typing import NDArray

# HiGHS drops matrix coefficients smaller than its small_matrix_value option
# (default 1e-9) and reports a warning, which highspy raises as an error when a
# row is added. Values this close to zero are floating point noise, such as
# interpolation across a forecast step edge, and are treated as exactly zero.
ZERO_TOLERANCE: Final = 1e-9


def clean_input_values(values: NDArray[Any]) -> NDArray[np.float64]:
    """Return values with magnitudes below ``ZERO_TOLERANCE`` snapped to exactly zero."""
    return np.where(np.abs(values) < ZERO_TOLERANCE, 0.0, values).astype(np.float64)


__all__ = ["ZERO_TOLERANCE", "clean_input_values"]
