"""Tests for naming and listing the rows of an infeasible model."""

import numpy as np
import pytest

from custom_components.haeo.core.model.infeasibility import MAX_LISTED_ROWS, RowLabel, listing, row_labels


def test_row_labels_give_periods_to_whole_blocks_and_mark_balance_rows() -> None:
    """Rows keep their constraint's name, get a period in whole-horizon blocks, and only balance rows are marked."""
    labels = row_labels(
        {
            "battery:charge": {"power_limit_power_limit": np.array([0, 1, 2, 3], dtype=np.int32)},
            "battery": {
                "energy": np.array([4, 5, 6], dtype=np.int32),
                "element_power_balance": np.array([7, 8, 9, 10], dtype=np.int32),
                "battery_soc_max": np.array([11, 12], dtype=np.int32),
            },
        },
        n_periods=2,
        balance_rows={7, 8},
    )

    assert labels == {
        0: RowLabel("battery:charge", "power_limit_power_limit", 0),
        1: RowLabel("battery:charge", "power_limit_power_limit", 1),
        2: RowLabel("battery:charge", "power_limit_power_limit", 0),
        3: RowLabel("battery:charge", "power_limit_power_limit", 1),
        4: RowLabel("battery", "energy", None),
        5: RowLabel("battery", "energy", None),
        6: RowLabel("battery", "energy", None),
        7: RowLabel("battery", "element_power_balance", 0, balance=True),
        8: RowLabel("battery", "element_power_balance", 1, balance=True),
        9: RowLabel("battery", "element_power_balance", 0),
        10: RowLabel("battery", "element_power_balance", 1),
        11: RowLabel("battery", "battery_soc_max", 0),
        12: RowLabel("battery", "battery_soc_max", 1),
    }


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        pytest.param(2, "row0, row1", id="short"),
        pytest.param(MAX_LISTED_ROWS, ", ".join(f"row{i}" for i in range(MAX_LISTED_ROWS)), id="at_the_limit"),
        pytest.param(
            MAX_LISTED_ROWS + 3,
            ", ".join(f"row{i}" for i in range(MAX_LISTED_ROWS)) + ", and 3 more",
            id="past_the_limit",
        ),
    ],
)
def test_listing_counts_the_rows_past_the_limit(count: int, expected: str) -> None:
    """A listing names its first rows and counts the rest."""
    assert listing(f"row{i}" for i in range(count)) == expected
