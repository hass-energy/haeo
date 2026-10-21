"""Tests for broadcast_to_sequence utility function."""

import numpy as np
from numpy.typing import NDArray
import pytest

from custom_components.haeo.core.model.util import broadcast_to_sequence


@pytest.mark.parametrize(
    ("value", "n_periods", "expected"),
    [
        pytest.param(np.array([1.0, 2.0, 3.0, 4.0, 5.0]), 3, [1.0, 2.0, 3.0], id="truncates_longer_sequence"),
        pytest.param(np.array([1.0, 2.0]), 5, [1.0, 2.0, 2.0, 2.0, 2.0], id="extends_shorter_sequence"),
        pytest.param(5.0, 3, [5.0, 5.0, 5.0], id="broadcasts_float"),
        pytest.param(5, 3, [5.0, 5.0, 5.0], id="broadcasts_int"),
        pytest.param(np.array([7.0]), 3, [7.0, 7.0, 7.0], id="broadcasts_single_element_array"),
        pytest.param(np.array([1.0, 2.0, 3.0]), 3, [1.0, 2.0, 3.0], id="exact_length"),
        pytest.param(np.array([1, 2, 3]), 3, [1.0, 2.0, 3.0], id="exact_length_ints"),
    ],
)
def test_broadcast_to_sequence(value: float | NDArray[np.float64], n_periods: int, expected: list[float]) -> None:
    """Values become a new, writable float array of n_periods values, extended by repeating the last one."""
    result = broadcast_to_sequence(value, n_periods=n_periods)

    np.testing.assert_array_equal(result, expected)
    assert result.dtype == np.float64
    assert result.flags.writeable
    assert not np.shares_memory(result, value)


def test_none_returns_none() -> None:
    """None input returns None."""
    result = broadcast_to_sequence(None, n_periods=3)
    assert result is None


def test_empty_raises() -> None:
    """Empty sequences raise ValueError."""
    with pytest.raises(ValueError, match="Sequence cannot be empty"):
        broadcast_to_sequence(np.array([]), n_periods=3)
