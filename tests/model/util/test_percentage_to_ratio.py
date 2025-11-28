"""Tests for percentage_to_ratio utility function."""

from custom_components.haeo.model.util import percentage_to_ratio


def test_single_value() -> None:
    """Single percentage value is converted to ratio list."""
    result = percentage_to_ratio(50.0)
    assert result == [0.5]


def test_sequence() -> None:
    """Sequence of percentages is converted to ratios."""
    result = percentage_to_ratio([25.0, 50.0, 75.0])
    assert result == [0.25, 0.5, 0.75]


def test_none_returns_none() -> None:
    """None input returns None."""
    result = percentage_to_ratio(None)
    assert result is None
