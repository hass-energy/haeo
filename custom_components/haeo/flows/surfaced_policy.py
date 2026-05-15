"""Surfaced policy rule management for element config flows.

Elements like battery and load surface policy pricing fields in their own
config flows. The underlying data lives in the single policy subentry as
rules. This module provides generic utilities to read, create, update, and
delete those rules from element flows.

Surfaced rules follow a pattern where one side is always a wildcard:
- source_is_wildcard=True:  ``* → {element_name}``
- source_is_wildcard=False: ``{element_name} → *``
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.constant_value import ConstantValue, as_constant_value
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.elements.policy import (
    CONF_PRICE,
    CONF_RULES,
    CONF_SOURCE,
    CONF_TARGET,
    PolicyRuleConfig,
)
from custom_components.haeo.core.schema.entity_value import EntityValue, as_entity_value, is_entity_value
from custom_components.haeo.core.schema.field_hints import SurfacedPriceHint
from custom_components.haeo.elements import has_surfaced_pricing

POLICIES_TITLE = "Policies"


def find_policy_subentry(hub_entry: ConfigEntry) -> ConfigSubentry | None:
    """Find the single policy subentry on a hub entry."""
    for subentry in hub_entry.subentries.values():
        if subentry.subentry_type == str(ElementType.POLICY):
            return subentry
    return None


def get_policy_rules(hub_entry: ConfigEntry) -> list[PolicyRuleConfig]:
    """Return the current list of policy rules, or empty if none exist."""
    subentry = find_policy_subentry(hub_entry)
    if subentry is None:
        return []
    return list(subentry.data.get(CONF_RULES, []))


def find_surfaced_rule(
    rules: list[PolicyRuleConfig],
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


def get_surfaced_rule_price(
    hub_entry: ConfigEntry,
    *,
    source: list[str] | None,
    target: list[str] | None,
) -> EntityValue | ConstantValue | None:
    """Get the price value of a surfaced rule, or None if no matching rule exists."""
    rules = get_policy_rules(hub_entry)
    idx = find_surfaced_rule(rules, source=source, target=target)
    if idx is None:
        return None
    return rules[idx].get(CONF_PRICE)


def save_surfaced_rule(
    hass: HomeAssistant,
    hub_entry: ConfigEntry,
    *,
    rule_name: str,
    source: list[str] | None,
    target: list[str] | None,
    price: EntityValue | ConstantValue | None,
) -> None:
    """Create, update, or delete a surfaced policy rule.

    If price is None, deletes the matching rule. Otherwise creates or
    updates the rule with the given price.
    """
    rules = get_policy_rules(hub_entry)
    idx = find_surfaced_rule(rules, source=source, target=target)

    if price is None:
        # Delete the rule if it exists
        if idx is not None:
            rules.pop(idx)
            _save_policy_rules(hass, hub_entry, rules)
        return

    rule: PolicyRuleConfig = {
        "name": rule_name,
        "enabled": True,
        "price": price,
    }
    if source:
        rule["source"] = source
    if target:
        rule["target"] = target

    if idx is not None:
        rules[idx] = rule
    else:
        rules.append(rule)

    _save_policy_rules(hass, hub_entry, rules)


def remove_element_surfaced_rules(
    hass: HomeAssistant,
    hub_entry: ConfigEntry,
    element_name: str,
) -> None:
    """Remove all surfaced policy rules associated with an element.

    Removes rules where the element appears as the sole member of
    source or target (the surfaced pattern). Called when an element
    subentry is deleted.
    """
    rules = get_policy_rules(hub_entry)
    original_count = len(rules)

    rules = [rule for rule in rules if not _is_surfaced_rule_for_element(rule, element_name)]

    if len(rules) != original_count:
        _save_policy_rules(hass, hub_entry, rules)


def _is_surfaced_rule_for_element(rule: PolicyRuleConfig, element_name: str) -> bool:
    """Check if a rule is a surfaced rule for the given element.

    A surfaced rule has one side as wildcard and the other as a
    single-element list containing the element name.
    """
    source = rule.get(CONF_SOURCE)
    target = rule.get(CONF_TARGET)

    # * → element_name pattern
    if not source and target == [element_name]:
        return True

    # element_name → * pattern
    return bool(source == [element_name] and not target)


def is_surfaced_pattern(
    hub_entry: ConfigEntry,
    source: list[str] | None,
    target: list[str] | None,
) -> bool:
    """Check if a source/target combination matches any element's surfaced pattern.

    Used by the standalone policy flow to prevent creating rules that
    conflict with element-surfaced patterns.
    """
    # A surfaced pattern has one wildcard side and one single-element side
    if source and not target and len(source) == 1:
        # element → * pattern: check if source element can have discharge cost
        return _element_has_surfaced_pricing(hub_entry, source[0])

    if not source and target and len(target) == 1:
        # * → element pattern: check if target element can have charge/consumption cost
        return _element_has_surfaced_pricing(hub_entry, target[0])

    return False


def _element_has_surfaced_pricing(hub_entry: ConfigEntry, element_name: str) -> bool:
    """Check if an element with the given name has surfaced pricing fields."""
    for subentry in hub_entry.subentries.values():
        if subentry.title != element_name:
            continue
        element_type = subentry.data.get(CONF_ELEMENT_TYPE)
        return isinstance(element_type, str) and has_surfaced_pricing(element_type)
    return False


def _save_policy_rules(
    hass: HomeAssistant,
    hub_entry: ConfigEntry,
    rules: list[PolicyRuleConfig],
) -> None:
    """Save policy rules to the policy subentry, creating it if needed."""
    subentry = find_policy_subentry(hub_entry)

    data: dict[str, Any] = {
        CONF_ELEMENT_TYPE: str(ElementType.POLICY),
        CONF_NAME: POLICIES_TITLE,
        CONF_RULES: rules,
    }

    if subentry is not None:
        hass.config_entries.async_update_subentry(hub_entry, subentry, data=data)
    elif rules:
        new_subentry = ConfigSubentry(
            data=MappingProxyType(data),
            subentry_type=str(ElementType.POLICY),
            title=POLICIES_TITLE,
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(hub_entry, new_subentry)


def price_to_form_value(price: EntityValue | ConstantValue | None) -> Any:
    """Convert a stored policy price to a form field value.

    Returns the raw value suitable for use with NormalizingChooseSelector defaults:
    - EntityValue → list[str] (entity IDs)
    - ConstantValue → float
    - None → None (no rule exists)
    """
    if price is None:
        return None
    if is_entity_value(price):
        return price["value"]
    return price["value"]


def form_value_to_price(value: Any) -> EntityValue | ConstantValue | None:
    """Convert a form field value back to a policy price.

    Handles the output from NormalizingChooseSelector:
    - list[str] → EntityValue
    - float/int → ConstantValue
    - None/empty → None (delete rule)
    """
    if value is None:
        return None
    if isinstance(value, list):
        if not value:
            return None
        return as_entity_value(value)
    if isinstance(value, (int, float)):
        return as_constant_value(float(value))
    return None  # pragma: no cover


# --- Flow helpers ---


def _resolve_endpoints(
    hint: SurfacedPriceHint,
    element_name: str,
) -> tuple[list[str] | None, list[str] | None]:
    """Resolve source and target for a surfaced price hint."""
    if hint.source_is_wildcard:
        return None, [element_name]
    return [element_name], None


def build_surfaced_defaults(
    hub_entry: ConfigEntry,
    element_name: str | None,
    surfaced_hints: dict[str, SurfacedPriceHint],
    surfaced_fields: Mapping[str, Any],
) -> dict[str, Any]:
    """Build default values for surfaced pricing fields.

    For new elements, uses the FieldHint defaults via get_choose_default.
    For existing elements, reads the current price from the policy subentry.
    """
    from custom_components.haeo.flows.field_schema import get_choose_default  # noqa: PLC0415

    defaults: dict[str, Any] = {}
    for field_name, hint in surfaced_hints.items():
        field_info = surfaced_fields.get(field_name)
        if field_info is None:
            continue

        if element_name is not None:
            source, target = _resolve_endpoints(hint, element_name)
            price = get_surfaced_rule_price(hub_entry, source=source, target=target)
            if price is not None:
                defaults[field_name] = price_to_form_value(price)
                continue

        default = get_choose_default(field_info, None)
        if default is not None:
            defaults[field_name] = default
    return defaults


def build_surfaced_schema_entries(
    surfaced_fields: Mapping[str, Any],
) -> dict[str, tuple[Any, Any]]:
    """Build vol.Schema entries for surfaced pricing fields.

    Uses the standard build_choose_selector to create selectors from the
    InputFieldInfo objects.
    """
    import voluptuous as vol  # noqa: PLC0415

    from custom_components.haeo.flows.field_schema import (  # noqa: PLC0415
        CHOICE_CONSTANT,
        CHOICE_ENTITY,
        CHOICE_NONE,
        build_choose_selector,
    )

    return {
        field_info.field_name: (
            vol.Optional(field_info.field_name),
            build_choose_selector(
                field_info,
                allowed_choices={CHOICE_ENTITY, CHOICE_CONSTANT, CHOICE_NONE},
                multiple=True,
                preferred_choice=CHOICE_CONSTANT,
            ),
        )
        for field_info in surfaced_fields.values()
    }


def save_surfaced_rules_from_input(
    hass: HomeAssistant,
    hub_entry: ConfigEntry,
    element_name: str,
    user_input: Mapping[str, Any],
    surfaced_hints: dict[str, SurfacedPriceHint],
    translations: Mapping[str, str],
) -> None:
    """Save surfaced policy rules from element config flow input.

    Reads the surfaced price field values from user_input and creates,
    updates, or deletes the corresponding policy rules.
    """
    for field_name, hint in surfaced_hints.items():
        raw_value = user_input.get(field_name)
        price = form_value_to_price(raw_value)
        source, target = _resolve_endpoints(hint, element_name)
        rule_name = translations.get(field_name, f"{element_name} {field_name}")
        save_surfaced_rule(
            hass,
            hub_entry,
            rule_name=rule_name,
            source=source,
            target=target,
            price=price,
        )
