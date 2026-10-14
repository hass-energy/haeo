"""Utility for separating duplicate timestamps in forecast data."""

import numpy as np
from numpy.typing import NDArray


def separate_duplicate_timestamps(
    timestamps: NDArray[np.float64],
    values: NDArray[np.float64],
) -> list[tuple[float, float]]:
    """Separate duplicate timestamps to prevent interpolation.

    When two adjacent timestamps are the same, this function adjusts the first
    occurrence to be slightly earlier using np.nextafter. This creates step
    functions without interpolation when forecasts are combined.

    When three or more consecutive timestamps are duplicates, middle entries are removed
    as they would cause issues when combining forecasts.

    Args:
        timestamps: Timestamps in seconds, in order
        values: The value at each timestamp

    Returns:
        List of (timestamp, value) tuples with duplicate timestamps separated

    """
    if not len(timestamps):
        return []

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
    return list(zip(adjusted_timestamps.tolist(), values.tolist(), strict=True))
