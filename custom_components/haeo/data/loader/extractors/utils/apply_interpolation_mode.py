"""Apply interpolation mode by generating synthetic timepoints."""

from collections.abc import Sequence

from custom_components.haeo.data.util import InterpolationMode

# Small epsilon for creating step transitions (1 millisecond)
EPSILON = 0.001

# Minimum points needed to apply interpolation mode (need at least 2 for transitions)
MIN_POINTS = 2


def apply_interpolation_mode(
    data: Sequence[tuple[float, float]],
    mode: InterpolationMode,
) -> list[tuple[float, float]]:
    """Apply interpolation mode by generating synthetic intermediate points.

    Converts non-linear interpolation into a series that behaves correctly
    with linear interpolation by adding synthetic points at transitions.

    Args:
        data: Sorted sequence of (timestamp, value) tuples
        mode: Interpolation mode to apply

    Returns:
        New series with synthetic points added for non-linear modes.
        For LINEAR mode, returns a copy of the original data.

    """
    if not data or len(data) < MIN_POINTS:
        return list(data)

    if mode == InterpolationMode.LINEAR:
        return list(data)

    if mode == InterpolationMode.PREVIOUS:
        return _apply_previous(data)

    if mode == InterpolationMode.NEXT:
        return _apply_next(data)

    if mode == InterpolationMode.NEAREST:
        return _apply_nearest(data)

    # Fallback for unknown modes - treat as linear
    return list(data)


def _apply_previous(data: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    """Apply PREVIOUS mode: hold previous value until next point.

    For each transition, add a synthetic point just before the new timestamp
    with the previous value, creating a step function.
    """
    result: list[tuple[float, float]] = []

    for i, (timestamp, value) in enumerate(data):
        if i > 0:
            # Add synthetic point just before this timestamp with previous value
            prev_value = data[i - 1][1]
            result.append((timestamp - EPSILON, prev_value))
        result.append((timestamp, value))

    return result


def _apply_next(data: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    """Apply NEXT mode: jump to next value immediately.

    For each point (except the last), add a synthetic point just after
    the timestamp with the next value, creating a forward step function.
    """
    result: list[tuple[float, float]] = []

    for i, (timestamp, value) in enumerate(data):
        result.append((timestamp, value))
        if i < len(data) - 1:
            # Add synthetic point just after this timestamp with next value
            next_value = data[i + 1][1]
            result.append((timestamp + EPSILON, next_value))

    return result


def _apply_nearest(data: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    """Apply NEAREST mode: use closest point's value.

    Add transition points at midpoints between consecutive timestamps
    where the value switches from one point's value to the next.
    """
    result: list[tuple[float, float]] = []

    for i, (timestamp, value) in enumerate(data):
        if i > 0:
            # Add transition at midpoint between previous and current
            prev_timestamp = data[i - 1][0]
            prev_value = data[i - 1][1]
            midpoint = (prev_timestamp + timestamp) / 2

            # Add synthetic point just before midpoint with previous value
            result.append((midpoint - EPSILON, prev_value))
            # Add synthetic point at midpoint with current value
            result.append((midpoint, value))

        result.append((timestamp, value))

    return result
