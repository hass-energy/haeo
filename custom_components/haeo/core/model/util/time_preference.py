"""Time preference weights for lexicographic ordering."""

from typing import Any

import numpy as np
from numpy.typing import NDArray


def time_preference_weights(periods: NDArray[np.floating[Any]], priority: int = 0) -> NDArray[np.float64]:
    """Return monotonically increasing weights for time preference ordering.

    Uses integer weights unique per priority level so that every
    (priority, time) pair gets a distinct coefficient.  This prevents
    primal degeneracy when multiple connections share a node and have
    equal marginal cost at the same time step.

    Weight for priority *p* at time *t* is ``p * n + (t + 1)``.
    Lower priority values produce smaller weights, making the solver
    prefer those connections when breaking ties.
    """
    n_periods = len(periods)
    return priority * n_periods + np.arange(1, n_periods + 1, dtype=np.float64)


__all__ = ["time_preference_weights"]
