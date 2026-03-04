"""Normalization helpers for test comparisons."""

from typing import Any

import numpy as np


def normalize_for_compare(value: Any) -> Any:
    """Normalize numpy arrays to lists for equality checks."""
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, list):
        return [normalize_for_compare(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_for_compare(val) for key, val in value.items()}
    return value
