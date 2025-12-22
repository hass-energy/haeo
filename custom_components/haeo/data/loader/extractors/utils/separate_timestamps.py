"""Utility for separating duplicate timestamps in forecast data."""

from collections.abc import Sequence

import numpy as np


def separate_duplicate_timestamps(data: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    """Separate duplicate timestamps to prevent interpolation.

    When two adjacent timestamps are the same, this function adjusts the first
    occurrence to be slightly earlier using np.nextafter. This creates step
    functions without interpolation when forecasts are combined.

    Args:
        data: Sequence of (timestamp, value) tuples

    Returns:
        List of (timestamp, value) tuples with duplicate timestamps separated

    """
    if not data:
        return []

    result: list[tuple[float, float]] = []
    prev_timestamp: float | None = None

    for timestamp, value in data:
        # If this timestamp equals the previous one, adjust the previous one
        if prev_timestamp is not None and timestamp == prev_timestamp:
            # Replace the last entry with a separated timestamp
            result[-1] = (np.nextafter(prev_timestamp, -np.inf), result[-1][1])

        result.append((timestamp, value))
        prev_timestamp = timestamp

    return result
