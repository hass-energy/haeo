"""Utility function to convert percentages to ratios."""

from collections.abc import Sequence
from typing import overload


@overload
def percentage_to_ratio(value: None) -> None: ...


@overload
def percentage_to_ratio(value: float | Sequence[float]) -> list[float]: ...


def percentage_to_ratio(
    value: float | Sequence[float] | None,
) -> list[float] | None:
    """Convert percentage (0-100) to ratio (0-1).

    Args:
        value: Percentage value, sequence of percentages, or None

    Returns:
        List of ratios (0-1), or None if input is None

    """
    if value is None:
        return None

    if isinstance(value, Sequence):
        return [v / 100.0 for v in value]

    return [value / 100.0]
