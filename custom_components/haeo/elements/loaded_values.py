"""Shared types for element input values."""

from collections.abc import Mapping
from typing import Any, TypeGuard

import numpy as np
from numpy.typing import NDArray

type LoadedValue = NDArray[np.floating[Any]] | bool
type LoadedValues = Mapping[str, LoadedValue]


def is_loaded_array(value: LoadedValue) -> TypeGuard[NDArray[np.floating[Any]]]:
    """Return True when value is a floating numpy array."""
    return isinstance(value, np.ndarray) and np.issubdtype(value.dtype, np.floating)


def require_loaded_array(value: LoadedValue, field_name: str) -> NDArray[np.floating[Any]]:
    """Return value when it's a floating array, otherwise raise."""
    if not is_loaded_array(value):
        msg = f"Expected float array for '{field_name}'"
        raise TypeError(msg)
    return value


def require_loaded_bool(value: LoadedValue, field_name: str) -> bool:
    """Return value when it's a bool, otherwise raise."""
    if not isinstance(value, bool):
        msg = f"Expected boolean for '{field_name}'"
        raise TypeError(msg)
    return value


__all__ = ["LoadedValue", "LoadedValues", "is_loaded_array", "require_loaded_array", "require_loaded_bool"]
