"""Tests for HAEO entity and device unique IDs."""

import pytest

from custom_components.haeo.unique_id import (
    ElementUniqueId,
    element_output_unique_id,
    element_unique_id,
    hub_unique_id,
    parse_element_unique_id,
)

ENTRY_ID = "01KDQ4A1B2C3D4E5F6G7H8J9KM"
SUBENTRY_ID = "01KDQ4N0PQRSTVWXYZ01234567"


@pytest.mark.parametrize(
    ("unique_id", "expected"),
    [
        pytest.param(
            element_unique_id(ENTRY_ID, SUBENTRY_ID, "price_source_target"),
            ElementUniqueId(SUBENTRY_ID, "price_source_target"),
            id="element_entity",
        ),
        pytest.param(
            element_output_unique_id(ENTRY_ID, SUBENTRY_ID, "grid", "grid_power_import"),
            ElementUniqueId(SUBENTRY_ID, "grid_grid_power_import"),
            id="element_output",
        ),
        pytest.param(hub_unique_id(ENTRY_ID, "auto_optimize"), None, id="hub_entity"),
        pytest.param(element_unique_id("01KDQ4OTHERENTRY0000000000", SUBENTRY_ID, "key"), None, id="other_entry"),
        pytest.param(element_unique_id(ENTRY_ID, "01kdq4n0pqrstvwxyz01234567", "key"), None, id="lowercase_id"),
        pytest.param(f"{ENTRY_ID}_{SUBENTRY_ID}", None, id="missing_key"),
        pytest.param(f"{ENTRY_ID}_{SUBENTRY_ID}_", None, id="empty_key"),
    ],
)
def test_parse_element_unique_id(unique_id: str, expected: ElementUniqueId | None) -> None:
    """Element IDs of the entry are split into subentry ID and key, and anything else is not parsed."""
    assert parse_element_unique_id(ENTRY_ID, unique_id) == expected
