"""Time preference weights for lexicographic ordering."""

from typing import Any

import numpy as np
from numpy.typing import NDArray


def time_preference_weights(periods: NDArray[np.floating[Any]]) -> NDArray[np.float64]:
    """Return monotonically increasing weights for time preference ordering.

    Uses a linear ramp from 0 to 1 across optimization periods so earlier
    energy transfer is preferred when objectives are otherwise equal.
    """
    n_periods = len(periods)
    if n_periods <= 1:
        return np.zeros(n_periods, dtype=np.float64)
    return np.arange(n_periods, dtype=np.float64) / float(n_periods - 1)


__all__ = ["time_preference_weights"]
