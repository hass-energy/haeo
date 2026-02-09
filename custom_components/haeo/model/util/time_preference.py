"""Time preference weights for lexicographic ordering."""

from typing import Any

import numpy as np
from numpy.typing import NDArray


def time_preference_weights(periods: NDArray[np.floating[Any]]) -> NDArray[np.float64]:
    """Return monotonically increasing weights for time preference ordering.

    Uses a 1..n ramp across optimization periods so earlier energy transfer is
    preferred when objectives are otherwise equal and each period has a nonzero
    contribution.
    """
    n_periods = len(periods)
    if n_periods <= 0:
        return np.zeros(0, dtype=np.float64)
    return 1e-4 * (np.arange(1, n_periods + 1, dtype=np.float64) / float(n_periods))


__all__ = ["time_preference_weights"]
