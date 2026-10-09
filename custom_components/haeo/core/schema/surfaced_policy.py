"""Policy rules surfaced as pricing fields on element forms.

Elements like battery and load surface policy pricing fields in their own
config. The underlying data lives in the single policy element as rules.

Surfaced rules follow a pattern where one side is always a wildcard:
- source_is_wildcard=True:  ``* → {element_name}``
- source_is_wildcard=False: ``{element_name} → *``
"""

from collections.abc import Mapping, Sequence
from typing import Any, Final

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema.elements.battery import SURFACED_PRICE_HINTS as BATTERY_SURFACED_PRICE_HINTS
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.elements.load import SURFACED_PRICE_HINTS as LOAD_SURFACED_PRICE_HINTS
from custom_components.haeo.core.schema.elements.policy import (
    CONF_PRICE,
    CONF_RULES,
    CONF_SOURCE,
    CONF_TARGET,
    PolicyRuleConfig,
)
from custom_components.haeo.core.schema.field_hints import SurfacedPriceHint

SURFACED_PRICE_HINTS_BY_TYPE: Final[dict[str, dict[str, SurfacedPriceHint]]] = {
    str(ElementType.BATTERY): BATTERY_SURFACED_PRICE_HINTS,
    str(ElementType.LOAD): LOAD_SURFACED_PRICE_HINTS,
}


def resolve_surfaced_endpoints(
    hint: SurfacedPriceHint,
    element_name: str,
) -> tuple[list[str] | None, list[str] | None]:
    """Resolve source and target for a surfaced price hint."""
    if hint.source_is_wildcard:
        return None, [element_name]
    return [element_name], None


def find_surfaced_rule(
    rules: Sequence[PolicyRuleConfig],
    *,
    source: list[str] | None,
    target: list[str] | None,
) -> int | None:
    """Find the index of a rule matching a surfaced pattern.

    A surfaced pattern has one wildcard side (represented as absent/empty)
    and one specific side (a single-element list).
    """
    for i, rule in enumerate(rules):
        rule_source = rule.get(CONF_SOURCE)
        rule_target = rule.get(CONF_TARGET)
        if _endpoints_match(rule_source, source) and _endpoints_match(rule_target, target):
            return i
    return None


def _endpoints_match(
    rule_value: list[str] | None,
    pattern: list[str] | None,
) -> bool:
    """Check if a rule endpoint matches a surfaced pattern endpoint.

    Both None/absent and empty list mean wildcard (*).
    """
    rule_normalized = rule_value if rule_value else None
    pattern_normalized = pattern if pattern else None
    return rule_normalized == pattern_normalized


def negated_price_paths(participants: Mapping[str, Mapping[str, Any]]) -> dict[str, frozenset[tuple[str, ...]]]:
    """Map each policy element name to the rule price paths that surface a negated price.

    Negated surfaced prices (e.g. load consumption cost) show a positive running
    value on the element form while the policy stores its negative. Constant
    prices are negated at the storage layer, but entity-driven prices can only be
    negated when resolved, so every resolver must negate the values at these paths.

    Args:
        participants: Map of element name to element config (sectioned format).

    Returns:
        Map of policy element name to ``(rules, index, price)`` field paths.

    """
    negated: dict[str, frozenset[tuple[str, ...]]] = {}
    for policy_name, policy_config in participants.items():
        if policy_config.get(CONF_ELEMENT_TYPE) != ElementType.POLICY:
            continue
        rules: list[PolicyRuleConfig] = list(policy_config.get(CONF_RULES, []))
        paths: set[tuple[str, ...]] = set()
        for element_name, element_config in participants.items():
            hints = SURFACED_PRICE_HINTS_BY_TYPE.get(str(element_config.get(CONF_ELEMENT_TYPE)), {})
            for hint in hints.values():
                if not hint.negate:
                    continue
                source, target = resolve_surfaced_endpoints(hint, element_name)
                index = find_surfaced_rule(rules, source=source, target=target)
                if index is not None:
                    paths.add((CONF_RULES, str(index), CONF_PRICE))
        negated[policy_name] = frozenset(paths)
    return negated


__all__ = [
    "SURFACED_PRICE_HINTS_BY_TYPE",
    "find_surfaced_rule",
    "negated_price_paths",
    "resolve_surfaced_endpoints",
]
