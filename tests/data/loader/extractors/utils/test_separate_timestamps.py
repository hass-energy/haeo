"""Tests for separate_timestamps utility."""


import numpy as np
import pytest

from custom_components.haeo.data.loader.extractors.utils import separate_duplicate_timestamps


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        # Empty data
        ([], []),
        # Single entry
        ([(100, 5.0)], [(100.0, 5.0)]),
        # No duplicates
        ([(100, 5.0), (200, 10.0), (300, 15.0)], [(100.0, 5.0), (200.0, 10.0), (300.0, 15.0)]),
        # One duplicate pair
        (
            [(100, 5.0), (100, 10.0)],
            [(np.nextafter(100.0, -np.inf), 5.0), (100.0, 10.0)],
        ),
        # Multiple duplicate pairs
        (
            [(100, 5.0), (100, 10.0), (200, 15.0), (200, 20.0)],
            [
                (np.nextafter(100.0, -np.inf), 5.0),
                (100.0, 10.0),
                (np.nextafter(200.0, -np.inf), 15.0),
                (200.0, 20.0),
            ],
        ),
        # Amber Electric step function pattern
        # Two adjacent windows: [1000, 1300) at 0.13 and [1300, 1600) at 0.15
        (
            [
                (1000, 0.13),  # Start of first window
                (1300, 0.13),  # End of first window
                (1300, 0.15),  # Start of second window (duplicate timestamp!)
                (1600, 0.15),  # End of second window
            ],
            [
                (1000.0, 0.13),  # Start unchanged
                (np.nextafter(1300.0, -np.inf), 0.13),  # End adjusted
                (1300.0, 0.15),  # Start unchanged
                (1600.0, 0.15),  # End unchanged
            ],
        ),
        # Mixed duplicates and non-duplicates
        (
            [(100, 1.0), (200, 2.0), (300, 3.0), (300, 4.0), (400, 5.0)],
            [
                (100.0, 1.0),
                (200.0, 2.0),
                (np.nextafter(300.0, -np.inf), 3.0),
                (300.0, 4.0),
                (400.0, 5.0),
            ],
        ),
        # Three consecutive duplicates - middle one should be removed
        (
            [(100, 1.0), (100, 2.0), (100, 3.0), (200, 4.0)],
            [
                (np.nextafter(100.0, -np.inf), 1.0),
                (100.0, 3.0),
                (200.0, 4.0),
            ],
        ),
        # Four consecutive duplicates - middle two should be removed
        (
            [(100, 1.0), (100, 2.0), (100, 3.0), (100, 4.0), (200, 5.0)],
            [
                (np.nextafter(100.0, -np.inf), 1.0),
                (100.0, 4.0),
                (200.0, 5.0),
            ],
        ),
        # Five consecutive duplicates - middle three should be removed
        (
            [(100, 1.0), (100, 2.0), (100, 3.0), (100, 4.0), (100, 5.0)],
            [
                (np.nextafter(100.0, -np.inf), 1.0),
                (100.0, 5.0),
            ],
        ),
    ],
    ids=[
        "empty",
        "single_entry",
        "no_duplicates",
        "one_duplicate_pair",
        "multiple_duplicate_pairs",
        "amber_step_function",
        "mixed_pattern",
        "three_consecutive_duplicates",
        "four_consecutive_duplicates",
        "five_consecutive_duplicates",
    ],
)
def test_separate_duplicate_timestamps(data: list[tuple[int, float]], expected: list[tuple[float, float]]) -> None:
    """Test timestamp separation with various patterns."""
    result = separate_duplicate_timestamps(data)
    assert result == expected


def test_separate_duplicate_timestamps_preserves_value_order() -> None:
    """Test that the function preserves the order of values (excluding removed middle duplicates)."""
    data = [(100, 1.0), (100, 2.0), (200, 3.0), (200, 4.0), (300, 5.0)]
    result = separate_duplicate_timestamps(data)

    # Values should be in same order
    values = [v for _, v in result]
    assert values == [1.0, 2.0, 3.0, 4.0, 5.0]
