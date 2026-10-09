"""Check values resolved from source entities before they reach the optimizer."""

from collections.abc import Mapping
from typing import Any, Final

import numpy as np
from numpy.typing import NDArray

# How far below zero a value for a non-negative input may fall, in the source's
# units, before it is rejected instead of clamped to zero. Sensors and forecasts
# often report small negative readings (a few watts) where zero is meant.
NEGATIVE_TOLERANCE: Final = 0.01


class InputError(ValueError):
    """A source supplied a value an input cannot use.

    The check that rejects the value names the translation key and placeholders
    describing the problem. Consumers report it through that key without knowing
    which check raised it.
    """

    def __init__(self, *, translation_key: str, translation_placeholders: Mapping[str, str]) -> None:
        """Record the translation describing the rejected value."""
        super().__init__(translation_key, dict(translation_placeholders))
        self.translation_key = translation_key
        self.translation_placeholders = dict(translation_placeholders)


def enforce_non_negative(values: NDArray[Any]) -> NDArray[np.float64]:
    """Return values with readings just below zero clamped to zero.

    Raises:
        InputError: If a value is further below zero than ``NEGATIVE_TOLERANCE``.

    """
    values = np.asarray(values, dtype=np.float64)
    if np.any(values < -NEGATIVE_TOLERANCE):
        raise InputError(
            translation_key="negative_input_value",
            translation_placeholders={"value": f"{float(values.min()):g}"},
        )
    return np.maximum(values, 0.0)


__all__ = ["NEGATIVE_TOLERANCE", "InputError", "enforce_non_negative"]
