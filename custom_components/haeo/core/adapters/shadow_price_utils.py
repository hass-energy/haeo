"""Helpers for re-expressing shadow prices in alternative units."""

from dataclasses import replace
from typing import Any

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.output_data import OutputData


def _aligned_periods(n_values: int, periods: NDArray[np.floating[Any]]) -> tuple[float, ...] | None:
    """Return a periods sequence of length n_values, repeating if n_values is a multiple of len(periods).

    Some shadow prices are per-tag-and-period (n_tags * n_periods values), in which case the
    same period applies across each tag block. Returns None when the lengths cannot be aligned.
    """
    n_periods = len(periods)
    if n_periods == 0:
        return None
    if n_values == n_periods:
        return tuple(float(p) for p in periods)
    if n_values % n_periods == 0:
        repeat = n_values // n_periods
        return tuple(float(p) for _ in range(repeat) for p in periods)
    return None


def shadow_price_per_energy(shadow: OutputData, periods: NDArray[np.floating[Any]]) -> OutputData | None:
    """Convert a $/kW shadow price into $/kWh by dividing by period length (h).

    Returns None when the shadow's value count cannot be aligned with periods (e.g. tagged
    shadows with non-multiple shape).
    """
    if shadow.unit != "$/kW":
        msg = f"shadow_price_per_energy expects $/kW, got {shadow.unit!r}"
        raise ValueError(msg)
    aligned = _aligned_periods(len(shadow.values), periods)
    if aligned is None:
        return None
    values = tuple(float(v) / p if p else 0.0 for v, p in zip(shadow.values, aligned, strict=True))
    return replace(shadow, unit="$/kWh", values=values)


def shadow_price_per_power(shadow: OutputData, periods: NDArray[np.floating[Any]]) -> OutputData | None:
    """Convert a $/kWh shadow price into $/kW by multiplying by period length (h).

    Returns None when the shadow's value count cannot be aligned with periods.
    """
    if shadow.unit != "$/kWh":
        msg = f"shadow_price_per_power expects $/kWh, got {shadow.unit!r}"
        raise ValueError(msg)
    aligned = _aligned_periods(len(shadow.values), periods)
    if aligned is None:
        return None
    values = tuple(float(v) * p for v, p in zip(shadow.values, aligned, strict=True))
    return replace(shadow, unit="$/kW", values=values)
