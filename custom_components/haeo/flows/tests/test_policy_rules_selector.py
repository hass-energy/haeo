"""Tests for the selector behind the policy element's rules."""

import pytest
import voluptuous as vol

from custom_components.haeo.core.schema import as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.flows.input_selector import InputSelectorConfig
from custom_components.haeo.flows.policy_rules_selector import (
    POLICY_RULES_STRINGS,
    POLICY_RULES_TRANSLATION_KEY,
    PolicyRulesSelector,
    PolicyRulesSelectorConfig,
)

PRICE: InputSelectorConfig = {
    "kinds": ["entity", "constant"],
    "value_type": "number",
    "domains": ["sensor"],
    "forecasts": {},
    "entities": ["sensor.price"],
}
CONFIG: PolicyRulesSelectorConfig = {
    "sources": [{"name": "Solar", "element_type": "solar"}, {"name": "Grid", "element_type": "grid"}],
    "targets": [{"name": "Grid", "element_type": "grid"}, {"name": "Load", "element_type": "load"}],
    "price": PRICE,
    "surfaced": [],
}


def test_selector_returns_each_rule_with_its_name_stripped_and_its_price_validated() -> None:
    """Rules come back in order, named without surrounding space, with ends as lists and the price as stored."""
    result = PolicyRulesSelector(CONFIG)(
        [
            {
                "name": "  Export  ",
                "enabled": False,
                "source": ["Solar"],
                "target": ["Grid"],
                "price": as_constant_value(0.02),
            },
            {"name": "Any to load", "price": {"type": "entity", "value": ["sensor.price"]}},
        ]
    )

    assert result == [
        {"name": "Export", "enabled": False, "source": ["Solar"], "target": ["Grid"], "price": as_constant_value(0.02)},
        {
            "name": "Any to load",
            "enabled": True,
            "source": [],
            "target": [],
            "price": as_entity_value(["sensor.price"]),
        },
    ]


def test_selector_keeps_a_rule_without_a_price_for_the_flow_to_report() -> None:
    """A rule left without a price comes back as none, so the flow can name the problem."""
    assert PolicyRulesSelector(CONFIG)([{"name": "A"}])[0]["price"] == as_none_value()


@pytest.mark.parametrize(
    "rules",
    [
        pytest.param({"name": "A"}, id="not_a_list"),
        pytest.param(["A"], id="rule_not_a_mapping"),
        pytest.param([{"name": "A", "source": ["Load"]}], id="source_that_cannot_source"),
        pytest.param([{"name": "A", "target": ["Solar"]}], id="target_that_cannot_sink"),
        pytest.param([{"name": "A", "price": {"type": "entity", "value": ["sensor.other"]}}], id="price_not_offered"),
    ],
)
def test_selector_rejects_rules_the_editor_does_not_offer(rules: object) -> None:
    """Each end names only elements offered for it, and the price only what its input offers."""
    with pytest.raises(vol.Invalid):
        PolicyRulesSelector(CONFIG)(rules)


def test_selector_lists_its_strings() -> None:
    """The element's labels are listed with the placeholders it fills in."""
    assert dict(PolicyRulesSelector.translation_strings()) == {
        ("selector", POLICY_RULES_TRANSLATION_KEY, "options", key): placeholders
        for key, placeholders in POLICY_RULES_STRINGS.items()
    }
