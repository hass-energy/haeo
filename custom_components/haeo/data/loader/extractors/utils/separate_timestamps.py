"""Utility for separating duplicate timestamps in forecast data."""

from collections.abc import Sequence

import numpy as np


def separate_duplicate_timestamps(data: Sequence[tuple[int, float]]) -> list[tuple[float, float]]:
    """Separate duplicate timestamps to prevent interpolation.

    When two adjacent timestamps are the same, this function adjusts the first
    occurrence to be slightly earlier using np.nextafter. This creates step
    functions without interpolation when forecasts are combined.

    When three or more consecutive timestamps are duplicates, middle entries are removed
    as they would cause issues when combining forecasts.

    Args:
        data: Sequence of (timestamp_seconds, value) tuples where timestamps are in seconds as integers

    Returns:
        List of (timestamp, value) tuples with duplicate timestamps separated and converted to floats

    """
    if not data:
        return []

    # Convert to numpy arrays for vectorized operations
    timestamps = np.array([t for t, _ in data], dtype=np.float64)
    values = np.array([v for _, v in data], dtype=np.float64)

    # Find where timestamps are duplicated with the next entry (compute once)
    is_duplicate_next = timestamps[:-1] == timestamps[1:]

    # Extend to full array length for easier indexing
    is_duplicate = np.concatenate([is_duplicate_next, [False]])
    is_duplicate_prev = np.concatenate([[False], is_duplicate_next])

    # Middle duplicates are entries that match both previous and next
    is_middle_duplicate = is_duplicate & is_duplicate_prev

    # Keep only non-middle-duplicates
    keep_mask = ~is_middle_duplicate
    timestamps = timestamps[keep_mask]
    values = values[keep_mask]
    is_duplicate = is_duplicate[keep_mask]

    # Apply nextafter to timestamps that are duplicated with the next entry
    adjusted_timestamps = np.where(is_duplicate, np.nextafter(timestamps, -np.inf), timestamps)

    # Convert to list of tuples
    return list(zip(adjusted_timestamps.tolist(), values.tolist(), strict=False))
