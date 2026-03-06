"""Time preference weights for lexicographic ordering."""

from typing import Any

import numpy as np
from numpy.typing import NDArray


def time_preference_weights(periods: NDArray[np.floating[Any]], connection_index: int = 0) -> NDArray[np.float64]:
    """Return monotonically increasing weights for time preference ordering.

    Uses integer weights unique per connection so that every (connection, time)
    pair gets a distinct coefficient.  This prevents primal degeneracy when
    multiple connections share a node and have equal marginal cost at the same
    time step.

    Weight for connection *c* at time *t* is ``c * n + (t + 1)``.
    """
    n_periods = len(periods)
    return connection_index * n_periods + np.arange(1, n_periods + 1, dtype=np.float64)


__all__ = ["time_preference_weights"]
