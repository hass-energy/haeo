"""The selector behind the policy element's rules.

Home Assistant renders a selector of type ``haeo_policy_rules`` as the
``ha-selector-haeo_policy_rules`` element from HAEO's selector bundle. The
element shows every rule as a card: its name, whether it is on, the elements its
power comes from and goes to (any element when none are chosen), and its price,
edited with the input element. A rule an element's own price field stands for
is marked with that element.
"""

from collections.abc import Iterator, Mapping
from typing import TypedDict

from homeassistant.helpers.selector import Selector
import voluptuous as vol

from custom_components.haeo.core.schema import SchemaValue
from custom_components.haeo.core.schema.elements.policy import (
    CONF_ENABLED,
    CONF_PRICE,
    CONF_RULE_NAME,
    CONF_SOURCE,
    CONF_TARGET,
)
from custom_components.haeo.flows.connection_selector import ConnectedElement
from custom_components.haeo.flows.input_selector import InputSelector, InputSelectorConfig

POLICY_RULES_SELECTOR_TYPE = "haeo_policy_rules"

# Translation key of the element's labels, under selector.<key>.options
POLICY_RULES_TRANSLATION_KEY = "policy_rules"

# The element's text: visible words and accessible labels, with the placeholders the element fills in
POLICY_RULES_STRINGS: dict[str, tuple[str, ...]] = {
    "add_endpoint": ("end",),
    "add_rule": (),
    "any": (),
    "enabled": ("rule",),
    "from": (),
    "price": ("rule",),
    "remove_rule": ("rule",),
    "rule_name": (),
    "to": (),
}


class SurfacedRule(TypedDict):
    """A rule pattern an element's own price field stands for: the element on one side, any on the other."""

    owner: str
    owner_type: str
    source: list[str] | None
    target: list[str] | None


class PolicyRulesSelectorConfig(TypedDict):
    """What the rules element offers: the elements each end can name, the price input, and surfaced patterns."""

    sources: list[ConnectedElement]
    targets: list[ConnectedElement]
    price: InputSelectorConfig
    surfaced: list[SurfacedRule]


class PolicyRuleValue(TypedDict):
    """A rule as the element reports it."""

    name: str
    enabled: bool
    source: list[str]
    target: list[str]
    price: SchemaValue


_ELEMENT = vol.Schema({vol.Required("name"): str, vol.Required("element_type"): str})


class PolicyRulesSelector(Selector[PolicyRulesSelectorConfig]):
    """Select the policy's rules."""

    selector_type = POLICY_RULES_SELECTOR_TYPE

    CONFIG_SCHEMA = vol.Schema(
        {
            vol.Required("sources"): [_ELEMENT],
            vol.Required("targets"): [_ELEMENT],
            vol.Required("price"): dict,
            vol.Required("surfaced"): [
                vol.Schema(
                    {
                        vol.Required("owner"): str,
                        vol.Required("owner_type"): str,
                        vol.Required("source"): vol.Any(None, [str]),
                        vol.Required("target"): vol.Any(None, [str]),
                    }
                )
            ],
        }
    )

    def __call__(self, data: object) -> list[PolicyRuleValue]:
        """Validate each rule's endpoints and price; names and duplicates are the flow's to check."""
        if not isinstance(data, list):
            msg = "Expected a list of rules"
            raise vol.Invalid(msg)
        return [self._rule(rule) for rule in data]

    def _rule(self, rule: object) -> PolicyRuleValue:
        if not isinstance(rule, Mapping):
            msg = "Expected a rule"
            raise vol.Invalid(msg)
        sources = vol.In([element["name"] for element in self.config["sources"]])
        targets = vol.In([element["name"] for element in self.config["targets"]])
        return {
            "name": str(rule.get(CONF_RULE_NAME, "")).strip(),
            "enabled": bool(rule.get(CONF_ENABLED, True)),
            "source": [sources(name) for name in _names(rule.get(CONF_SOURCE))],
            "target": [targets(name) for name in _names(rule.get(CONF_TARGET))],
            "price": InputSelector(self.config["price"])(rule.get(CONF_PRICE, {"type": "none"})),
        }

    @staticmethod
    def translation_strings() -> Iterator[tuple[tuple[str, ...], tuple[str, ...]]]:
        """Yield the path of every label the element gives its controls, with the placeholders it fills in."""
        for key, placeholders in POLICY_RULES_STRINGS.items():
            yield ("selector", POLICY_RULES_TRANSLATION_KEY, "options", key), placeholders


def _names(value: object) -> list[object]:
    """Return an end's element names; an end with none means any element."""
    return list(value) if isinstance(value, list | tuple) else []


__all__ = [
    "POLICY_RULES_SELECTOR_TYPE",
    "POLICY_RULES_STRINGS",
    "POLICY_RULES_TRANSLATION_KEY",
    "PolicyRuleValue",
    "PolicyRulesSelector",
    "PolicyRulesSelectorConfig",
    "SurfacedRule",
]
