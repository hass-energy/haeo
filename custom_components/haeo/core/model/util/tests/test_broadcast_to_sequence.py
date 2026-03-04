"""Tests for broadcast_to_sequence utility function."""

import numpy as np
import pytest

from custom_components.haeo.core.model.util import broadcast_to_sequence


def test_truncates_longer_sequence() -> None:
    """Sequences longer than n_periods are truncated."""
    result = broadcast_to_sequence(np.array([1.0, 2.0, 3.0, 4.0, 5.0]), n_periods=3)
    assert isinstance(result, np.ndarray)
    np.testing.assert_array_equal(result, [1.0, 2.0, 3.0])


def test_extends_shorter_sequence() -> None:
    """Sequences shorter than n_periods are extended by repeating the last value."""
    result = broadcast_to_sequence(np.array([1.0, 2.0]), n_periods=5)
    assert isinstance(result, np.ndarray)
    np.testing.assert_array_equal(result, [1.0, 2.0, 2.0, 2.0, 2.0])


def test_broadcasts_single_value() -> None:
    """Single values are broadcast to n_periods length."""
    result = broadcast_to_sequence(5.0, n_periods=3)
    assert isinstance(result, np.ndarray)
    np.testing.assert_array_equal(result, [5.0, 5.0, 5.0])


def test_exact_length_unchanged() -> None:
    """Sequences matching n_periods are returned unchanged."""
    result = broadcast_to_sequence(np.array([1.0, 2.0, 3.0]), n_periods=3)
    assert isinstance(result, np.ndarray)
    np.testing.assert_array_equal(result, [1.0, 2.0, 3.0])


def test_none_returns_none() -> None:
    """None input returns None."""
    result = broadcast_to_sequence(None, n_periods=3)
    assert result is None


def test_empty_raises() -> None:
    """Empty sequences raise ValueError."""
    with pytest.raises(ValueError, match="Sequence cannot be empty"):
        broadcast_to_sequence(np.array([]), n_periods=3)
