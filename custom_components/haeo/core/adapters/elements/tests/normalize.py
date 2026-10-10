"""Normalization helpers for test comparisons."""

from collections.abc import Mapping, Sequence

import numpy as np


def normalize_for_compare(value: object) -> object:
    """Normalize numpy arrays to lists for equality checks."""
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, list):
        return [normalize_for_compare(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_for_compare(val) for key, val in value.items()}
    return value


def segment_order(elements: Sequence[Mapping[str, object]]) -> list[list[str]]:
    """Return each model element's segment names in order; segment order sets where limits apply."""
    order: list[list[str]] = []
    for element in elements:
        segments = element.get("segments")
        order.append([str(name) for name in segments] if isinstance(segments, Mapping) else [])
    return order
