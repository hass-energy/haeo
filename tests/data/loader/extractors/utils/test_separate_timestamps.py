"""Tests for separate_timestamps utility."""

import numpy as np
import pytest

from custom_components.haeo.data.loader.extractors.utils import separate_duplicate_timestamps


def test_separate_duplicate_timestamps_empty() -> None:
    """Test with empty data."""
    result = separate_duplicate_timestamps([])
    assert result == []


def test_separate_duplicate_timestamps_single_entry() -> None:
    """Test with single entry."""
    data = [(100.0, 5.0)]
    result = separate_duplicate_timestamps(data)
    assert result == [(100.0, 5.0)]


def test_separate_duplicate_timestamps_no_duplicates() -> None:
    """Test with no duplicate timestamps."""
    data = [(100.0, 5.0), (200.0, 10.0), (300.0, 15.0)]
    result = separate_duplicate_timestamps(data)
    assert result == [(100.0, 5.0), (200.0, 10.0), (300.0, 15.0)]


def test_separate_duplicate_timestamps_one_duplicate_pair() -> None:
    """Test with one pair of duplicate timestamps."""
    data = [(100.0, 5.0), (100.0, 10.0)]
    result = separate_duplicate_timestamps(data)

    assert len(result) == 2
    assert result[0][1] == 5.0  # First value unchanged
    assert result[1] == (100.0, 10.0)  # Second timestamp/value unchanged
    assert result[0][0] == np.nextafter(100.0, -np.inf)  # First timestamp adjusted


def test_separate_duplicate_timestamps_multiple_duplicates() -> None:
    """Test with multiple pairs of duplicate timestamps."""
    data = [
        (100.0, 5.0),
        (100.0, 10.0),
        (200.0, 15.0),
        (200.0, 20.0),
    ]
    result = separate_duplicate_timestamps(data)

    assert len(result) == 4
    # First pair
    assert result[0][0] == np.nextafter(100.0, -np.inf)
    assert result[0][1] == 5.0
    assert result[1] == (100.0, 10.0)
    # Second pair
    assert result[2][0] == np.nextafter(200.0, -np.inf)
    assert result[2][1] == 15.0
    assert result[3] == (200.0, 20.0)


def test_separate_duplicate_timestamps_amber_pattern() -> None:
    """Test with Amber Electric step function pattern.

    Each forecast window should produce two points:
    (start, price) and (end, price) to create step function.
    When windows are adjacent, the end of one equals the start of the next.
    """
    # Simulate what Amber extractors should produce after the change
    # Two adjacent windows: [1000, 1300) at 0.13 and [1300, 1600) at 0.15
    data = [
        (1000.0, 0.13),  # Start of first window
        (1300.0, 0.13),  # End of first window
        (1300.0, 0.15),  # Start of second window (duplicate timestamp!)
        (1600.0, 0.15),  # End of second window
    ]

    result = separate_duplicate_timestamps(data)

    assert len(result) == 4
    # First window
    assert result[0] == (1000.0, 0.13)  # Start unchanged
    assert result[1][0] == np.nextafter(1300.0, -np.inf)  # End adjusted
    assert result[1][1] == 0.13
    # Second window boundary (duplicate at 1300.0 was separated)
    assert result[2] == (1300.0, 0.15)  # Start unchanged
    assert result[3] == (1600.0, 0.15)  # End unchanged


def test_separate_duplicate_timestamps_preserves_order() -> None:
    """Test that the function preserves the order of entries."""
    data = [(100.0, 1.0), (100.0, 2.0), (200.0, 3.0), (200.0, 4.0), (300.0, 5.0)]
    result = separate_duplicate_timestamps(data)

    # Values should be in same order
    values = [v for _, v in result]
    assert values == [1.0, 2.0, 3.0, 4.0, 5.0]


def test_separate_duplicate_timestamps_mixed_pattern() -> None:
    """Test with mixed duplicates and non-duplicates."""
    data = [
        (100.0, 1.0),
        (200.0, 2.0),  # No duplicate
        (300.0, 3.0),
        (300.0, 4.0),  # Duplicate
        (400.0, 5.0),  # No duplicate
    ]
    result = separate_duplicate_timestamps(data)

    assert len(result) == 5
    assert result[0] == (100.0, 1.0)
    assert result[1] == (200.0, 2.0)
    assert result[2][0] == np.nextafter(300.0, -np.inf)
    assert result[2][1] == 3.0
    assert result[3] == (300.0, 4.0)
    assert result[4] == (400.0, 5.0)
