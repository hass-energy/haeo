"""Surfaced policy rule management for element config flows.

Elements like battery and load surface policy pricing fields in their own
config flows. The underlying data lives in the single policy subentry as
rules. This module provides utilities to read, create, update, and delete
those rules from element flows.

Surfaced rules follow a pattern where one side is always a wildcard:
- Battery charge cost: * → {battery_name}
- Battery discharge cost: {battery_name} → *
- Load consumption cost: * → {load_name}
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
import voluptuous as vol

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.constant_value import ConstantValue, as_constant_value, is_constant_value
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.elements.policy import (
    CONF_PRICE,
    CONF_RULES,
    CONF_SOURCE,
    CONF_TARGET,
    PolicyRuleConfig,
)
from custom_components.haeo.core.schema.entity_value import EntityValue, as_entity_value, is_entity_value

POLICIES_TITLE = "Policies"

# Config key for surfaced charge cost on battery
CONF_CHARGE_COST = "charge_cost"

# Config key for surfaced discharge cost on battery
CONF_DISCHARGE_COST = "discharge_cost"

# Config key for surfaced consumption cost on load
CONF_CONSUMPTION_COST = "consumption_cost"


@dataclass(frozen=True, slots=True)
class SurfacedRuleSpec:
    """Specification for a surfaced policy rule field on an element."""

    field_name: str
    source_is_wildcard: bool
    default_value: float
    rule_name_key: str


# Battery surfaced rule specifications
BATTERY_SURFACED_RULES: tuple[SurfacedRuleSpec, ...] = (
    SurfacedRuleSpec(
        field_name=CONF_CHARGE_COST,
        source_is_wildcard=True,
        default_value=-0.001,
        rule_name_key="charge_cost",
    ),
    SurfacedRuleSpec(
        field_name=CONF_DISCHARGE_COST,
        source_is_wildcard=False,
        default_value=0.0,
        rule_name_key="discharge_cost",
    ),
)

# Load surfaced rule specifications
LOAD_SURFACED_RULES: tuple[SurfacedRuleSpec, ...] = (
    SurfacedRuleSpec(
        field_name=CONF_CONSUMPTION_COST,
        source_is_wildcard=True,
        default_value=0.0,
        rule_name_key="consumption_cost",
    ),
)


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

    rules = [
        rule
        for rule in rules
        if not _is_surfaced_rule_for_element(rule, element_name)
    ]

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
        return element_type in (str(ElementType.BATTERY), str(ElementType.LOAD))
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
    if is_constant_value(price):
        return price["value"]
    return None


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
    return None


# --- Higher-level helpers for element config flows ---


def _resolve_endpoints(
    spec: SurfacedRuleSpec,
    element_name: str,
) -> tuple[list[str] | None, list[str] | None]:
    """Resolve source and target for a surfaced rule spec."""
    if spec.source_is_wildcard:
        return None, [element_name]
    return [element_name], None


def build_surfaced_price_defaults(
    hub_entry: ConfigEntry,
    element_name: str | None,
    specs: tuple[SurfacedRuleSpec, ...],
) -> dict[str, Any]:
    """Build default values for surfaced price fields.

    For new elements, returns the spec's default_value.
    For existing elements, reads the current price from the policy subentry.
    """
    defaults: dict[str, Any] = {}
    for spec in specs:
        if element_name is None:
            # New element: use default
            defaults[spec.field_name] = spec.default_value
        else:
            source, target = _resolve_endpoints(spec, element_name)
            price = get_surfaced_rule_price(hub_entry, source=source, target=target)
            defaults[spec.field_name] = price_to_form_value(price) if price is not None else spec.default_value
    return defaults


def build_surfaced_price_schema_entries(
    specs: tuple[SurfacedRuleSpec, ...],
    price_selector: Any,
) -> dict[str, tuple[vol.Marker, Any]]:
    """Build vol.Schema entries for surfaced price fields.

    Returns a dict of field_name → (vol.Optional marker, selector) suitable
    for injecting into a section's extra_field_entries.
    """
    return {
        spec.field_name: (vol.Optional(spec.field_name), price_selector)
        for spec in specs
    }


def build_surfaced_price_selector() -> Any:
    """Build a NormalizingChooseSelector for surfaced price fields.

    Uses the same price field metadata as the policy flow to ensure
    consistent entity filtering and number constraints.
    """
    # Deferred imports to avoid circular imports at module level
    from custom_components.haeo.core.schema.elements.policy import CONF_PRICE as POLICY_CONF_PRICE  # noqa: PLC0415
    from custom_components.haeo.core.schema.elements.policy import CONF_RULES as POLICY_CONF_RULES  # noqa: PLC0415
    from custom_components.haeo.core.schema.elements.policy import ELEMENT_TYPE as POLICY_ELEMENT_TYPE  # noqa: PLC0415
    from custom_components.haeo.elements import get_list_input_fields  # noqa: PLC0415
    from custom_components.haeo.flows.field_schema import (  # noqa: PLC0415
        CHOICE_CONSTANT,
        CHOICE_ENTITY,
        CHOICE_NONE,
        build_choose_selector,
    )

    dummy_config: dict[str, Any] = {
        CONF_ELEMENT_TYPE: str(POLICY_ELEMENT_TYPE),
        POLICY_CONF_RULES: [{"name": "_", POLICY_CONF_PRICE: {"type": "constant", "value": 0}}],
    }
    list_fields = get_list_input_fields(dummy_config)
    section = next(iter(list_fields.values()))
    field_info = section[POLICY_CONF_PRICE]
    return build_choose_selector(
        field_info,
        allowed_choices={CHOICE_ENTITY, CHOICE_CONSTANT, CHOICE_NONE},
        multiple=True,
        preferred_choice=CHOICE_CONSTANT,
    )


def save_surfaced_rules_from_input(
    hass: HomeAssistant,
    hub_entry: ConfigEntry,
    element_name: str,
    user_input: Mapping[str, Any],
    specs: tuple[SurfacedRuleSpec, ...],
    translations: Mapping[str, str],
) -> None:
    """Save surfaced policy rules from element config flow input.

    Reads the surfaced price field values from user_input and creates,
    updates, or deletes the corresponding policy rules.
    """
    for spec in specs:
        raw_value = user_input.get(spec.field_name)
        price = form_value_to_price(raw_value)
        source, target = _resolve_endpoints(spec, element_name)
        rule_name = translations.get(spec.rule_name_key, f"{element_name} {spec.field_name}")
        save_surfaced_rule(
            hass,
            hub_entry,
            rule_name=rule_name,
            source=source,
            target=target,
            price=price,
        )
