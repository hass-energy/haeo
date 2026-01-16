"""Tests for percentage_to_ratio utility function."""

import numpy as np

from custom_components.haeo.model.util import percentage_to_ratio


def test_single_value() -> None:
    """Single percentage value is converted to ratio array."""
    result = percentage_to_ratio(np.array(50.0))
    np.testing.assert_array_equal(result, 0.5)


def test_sequence() -> None:
    """Sequence of percentages is converted to ratios."""
    result = percentage_to_ratio(np.array([25.0, 50.0, 75.0]))
    np.testing.assert_array_equal(result, [0.25, 0.5, 0.75])


def test_none_returns_none() -> None:
    """None input returns None."""
    result = percentage_to_ratio(None)
    assert result is None
