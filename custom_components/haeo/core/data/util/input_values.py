"""Clean values resolved from source entities before they reach the optimizer."""

from typing import Any, Final

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.util.solver_rows import SMALL_MATRIX_VALUE

# How far below zero a value for a non-negative input may fall, in the source's
# units, before it is rejected instead of clamped to zero. Sensors and forecasts
# often report small negative readings (a few watts) where zero is meant.
NEGATIVE_TOLERANCE: Final = 0.01


class NegativeInputError(ValueError):
    """A source supplied a significantly negative value for a non-negative input."""

    def __init__(self, value: float) -> None:
        """Record the offending value."""
        super().__init__(f"Value {value:g} is below the minimum of zero for this input")
        self.value = value


def clean_input_values(values: NDArray[Any], *, non_negative: bool) -> NDArray[np.float64]:
    """Return values with float noise snapped to zero and non-negativity enforced.

    Magnitudes below ``SMALL_MATRIX_VALUE`` are floating point noise, such as
    interpolation across a forecast step edge, and become exactly zero. For non-negative
    inputs, values within ``NEGATIVE_TOLERANCE`` below zero are clamped to zero.

    Raises:
        NegativeInputError: If a non-negative input has a value further below zero
            than ``NEGATIVE_TOLERANCE``.

    """
    cleaned = np.where(np.abs(values) < SMALL_MATRIX_VALUE, 0.0, values).astype(np.float64)
    if not non_negative:
        return cleaned

    if np.any(cleaned < -NEGATIVE_TOLERANCE):
        raise NegativeInputError(float(cleaned.min()))

    return np.where(cleaned < 0.0, 0.0, cleaned)


__all__ = ["NEGATIVE_TOLERANCE", "NegativeInputError", "clean_input_values"]
