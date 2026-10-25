"""Tests for finding and renaming the elements an element's config names."""

import pytest

from custom_components.haeo.core.schema import as_connection_target, as_constant_value
from custom_components.haeo.core.schema.elements import ElementType, map_element_references, referenced_element_names

REFERENCE_CASES = [
    pytest.param(
        ElementType.CONNECTION,
        {
            "element_type": ElementType.CONNECTION,
            "name": "Link",
            "endpoints": {"source": as_connection_target("Bus"), "target": as_connection_target("Inverter")},
        },
        {"Bus", "Inverter"},
        id="connection_endpoints",
    ),
    pytest.param(
        ElementType.LOAD,
        {
            "element_type": ElementType.LOAD,
            "name": "House",
            "connection": as_connection_target("Bus"),
            "nested": [{"deeper": as_connection_target("Inverter")}],
        },
        {"Bus", "Inverter"},
        id="connection_targets_nested_anywhere",
    ),
    pytest.param(
        ElementType.BUFFER,
        {
            "element_type": ElementType.BUFFER,
            "name": "Backup",
            "kind": "reserve",
            "participants": {"loads": ["House"], "generation": ["Solar"], "storage": ["Battery"]},
        },
        {"House", "Solar", "Battery"},
        id="buffer_participants",
    ),
    pytest.param(
        ElementType.POLICY,
        {
            "element_type": ElementType.POLICY,
            "name": "Policies",
            "rules": [
                {"name": "out", "enabled": True, "source": ["Battery", "Solar"], "price": as_constant_value(0.1)},
                {"name": "in", "enabled": True, "target": ["House"], "price": as_constant_value(0.2)},
                {"name": "any", "enabled": True, "price": as_constant_value(0.3)},
            ],
        },
        {"Battery", "Solar", "House"},
        id="policy_rule_sides",
    ),
    pytest.param(
        ElementType.JUNCTION,
        {"element_type": ElementType.JUNCTION, "name": "Switchboard"},
        set(),
        id="names_nothing",
    ),
]


@pytest.mark.parametrize(("element_type", "config", "expected"), REFERENCE_CASES)
def test_referenced_element_names(element_type: ElementType, config: dict[str, object], expected: set[str]) -> None:
    """Every element a config names is found, whether as a connection target or in a list."""
    assert referenced_element_names(element_type, config) == expected


@pytest.mark.parametrize(("element_type", "config", "expected"), REFERENCE_CASES)
def test_map_element_references_renames_every_reference(
    element_type: ElementType, config: dict[str, object], expected: set[str]
) -> None:
    """Renaming every name an element holds leaves it naming only the new names."""
    mapped = map_element_references(element_type, config, lambda name: f"New {name}")

    assert referenced_element_names(element_type, mapped) == {f"New {name}" for name in expected}
    assert mapped["name"] == config["name"]


@pytest.mark.parametrize(
    ("element_type", "config", "expected"),
    [
        pytest.param(
            ElementType.BUFFER,
            {"name": "Backup", "participants": {"loads": ["House"], "storage": ["Old", "New"]}},
            {"name": "Backup", "participants": {"loads": ["House"], "storage": ["New"]}},
            id="buffer_lists_a_participant_once",
        ),
        pytest.param(
            ElementType.POLICY,
            {
                "name": "Policies",
                "rules": [
                    {"name": "Old charge cost", "target": ["Old"], "price": 0.1},
                    {"name": "both out", "source": ["Old", "New"], "price": 0.2},
                    {"name": "New charge cost", "target": ["New"], "price": 0.3},
                ],
            },
            {
                "name": "Policies",
                "rules": [
                    {"name": "Old charge cost", "target": ["New"], "price": 0.1},
                    {"name": "both out", "source": ["New"], "price": 0.2},
                ],
            },
            id="policy_keeps_the_first_rule_over_the_same_elements",
        ),
    ],
)
def test_renaming_onto_a_name_still_referenced_leaves_no_duplicates(
    element_type: ElementType, config: dict[str, object], expected: dict[str, object]
) -> None:
    """Renaming an element to the name of a deleted one it still shares a config with names it once."""
    assert map_element_references(element_type, config, lambda name: "New" if name == "Old" else name) == expected
