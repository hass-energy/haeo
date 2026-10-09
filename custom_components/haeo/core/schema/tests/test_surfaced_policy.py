"""Tests for surfaced policy rule lookup and negated price paths."""

import pytest

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema import as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.elements.policy import CONF_PRICE, CONF_RULES, PolicyRuleConfig
from custom_components.haeo.core.schema.surfaced_policy import find_surfaced_rule, negated_price_paths

# --- find_surfaced_rule tests ---


@pytest.mark.parametrize(
    ("rules", "source", "target", "expected_index"),
    [
        pytest.param([], None, ["Battery"], None, id="empty_rules"),
        pytest.param(
            [{"name": "r1", "target": ["Battery"], "price": as_constant_value(0.1)}],
            None,
            ["Battery"],
            0,
            id="wildcard_to_element",
        ),
        pytest.param(
            [{"name": "r1", "source": ["Battery"], "price": as_constant_value(0.1)}],
            ["Battery"],
            None,
            0,
            id="element_to_wildcard",
        ),
        pytest.param(
            [
                {"name": "r1", "source": ["Other"], "price": as_constant_value(0.1)},
                {"name": "r2", "target": ["Battery"], "price": as_constant_value(0.2)},
            ],
            None,
            ["Battery"],
            1,
            id="second_rule_matches",
        ),
        pytest.param(
            [{"name": "r1", "source": ["A"], "target": ["B"], "price": as_constant_value(0.1)}],
            None,
            ["B"],
            None,
            id="both_sides_set_no_match",
        ),
    ],
)
def test_find_surfaced_rule(
    rules: list[PolicyRuleConfig],
    source: list[str] | None,
    target: list[str] | None,
    expected_index: int | None,
) -> None:
    """Finds the correct rule index by endpoint pattern."""
    assert find_surfaced_rule(rules, source=source, target=target) == expected_index


def test_negated_price_paths_flags_load_consumption_rule() -> None:
    """A wildcard-to-load rule is flagged; a battery charge rule is not."""
    participants: dict[str, dict[str, object]] = {
        "Miner": {CONF_ELEMENT_TYPE: ElementType.LOAD},
        "Battery": {CONF_ELEMENT_TYPE: ElementType.BATTERY},
        "Policies": {
            CONF_ELEMENT_TYPE: ElementType.POLICY,
            CONF_RULES: [
                {"name": "charge", "target": ["Battery"], "price": as_constant_value(0.1)},
                {"name": "miner", "target": ["Miner"], "price": as_entity_value(["sensor.doge"])},
            ],
        },
    }

    assert negated_price_paths(participants) == {"Policies": frozenset({(CONF_RULES, "1", CONF_PRICE)})}


def test_negated_price_paths_keeps_stored_rule_indices() -> None:
    """A rules entry that is not a mapping does not shift the index of the rules after it."""
    participants: dict[str, dict[str, object]] = {
        "Miner": {CONF_ELEMENT_TYPE: ElementType.LOAD},
        "Policies": {
            CONF_ELEMENT_TYPE: ElementType.POLICY,
            CONF_RULES: (
                "not a rule",
                {"name": "miner", "target": ["Miner"], "price": as_entity_value(["sensor.doge"])},
            ),
        },
    }

    assert negated_price_paths(participants) == {"Policies": frozenset({(CONF_RULES, "1", CONF_PRICE)})}


def test_negated_price_paths_without_policy_is_empty() -> None:
    """Configs without a policy element have no negated paths."""
    assert negated_price_paths({"Miner": {CONF_ELEMENT_TYPE: ElementType.LOAD}, "orphan": {}}) == {}
