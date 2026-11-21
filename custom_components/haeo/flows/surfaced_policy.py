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

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
import voluptuous as vol

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.data.loader.extractors import EntityMetadata
from custom_components.haeo.core.schema.constant_value import ConstantValue, as_constant_value, is_constant_value
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.elements.policy import CONF_ENABLED, CONF_PRICE, CONF_RULES, PolicyRuleConfig
from custom_components.haeo.core.schema.entity_value import EntityValue, is_entity_value
from custom_components.haeo.core.schema.field_hints import SurfacedPriceHint
from custom_components.haeo.core.schema.none_value import NoneValue, as_none_value
from custom_components.haeo.core.schema.surfaced_policy import find_surfaced_rule, resolve_surfaced_endpoints
from custom_components.haeo.core.units import currency_symbol
from custom_components.haeo.elements.input_fields import AnyInputFieldInfo, localize_input_field
from custom_components.haeo.flows.element_flow import build_inclusion_map
from custom_components.haeo.flows.field_schema import build_input_selector, get_input_default
from custom_components.haeo.flows.input_selector import InputKind, InputSelector

POLICIES_TITLE = "Policies"

# Surfaced fields can be an entity, a constant, or none.
SURFACED_KINDS: tuple[InputKind, ...] = ("entity", "constant", "none")


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

    If price is None, deletes the matching rule. Otherwise creates the rule
    enabled, or updates the rule's price keeping whether it is enabled.
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
        "enabled": rules[idx][CONF_ENABLED] if idx is not None else as_constant_value(value=True),
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


def _save_policy_rules(
    hass: HomeAssistant,
    hub_entry: ConfigEntry,
    rules: list[PolicyRuleConfig],
) -> None:
    """Save policy rules to the policy subentry, creating it if needed."""
    subentry = find_policy_subentry(hub_entry)

    data: dict[str, object] = {
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


def _negate_price(price: EntityValue | ConstantValue | None) -> EntityValue | ConstantValue | None:
    """Negate a stored constant price, leaving entity prices untouched."""
    if price is not None and is_constant_value(price):
        return as_constant_value(-price["value"])
    return price


def form_value_to_price(value: object) -> EntityValue | ConstantValue | None:
    """Return the price a submitted field sets, or None when it sets none."""
    if is_entity_value(value) or is_constant_value(value):
        return value
    return None


# --- Flow helpers ---


def build_surfaced_defaults(
    hub_entry: ConfigEntry,
    element_name: str | None,
    surfaced_hints: dict[str, SurfacedPriceHint],
    surfaced_fields: Mapping[str, AnyInputFieldInfo],
) -> dict[str, object]:
    """Build default values for surfaced pricing fields.

    For new elements, uses the FieldHint defaults via get_input_default.
    For existing elements, reads the current price from the policy subentry.
    If an existing element has no matching rule, the field opens with none
    (the rule was unlinked or never created).
    """
    defaults: dict[str, object] = {}
    prices = get_surfaced_prices(hub_entry, element_name, surfaced_hints) if element_name is not None else None
    for field_name, hint in surfaced_hints.items():
        field_info = surfaced_fields.get(field_name)
        if field_info is None:
            continue

        if prices is not None:
            price = prices[field_name]
            defaults[field_name] = _negate_price(price) if hint.negate and is_constant_value(price) else price
            continue

        defaults[field_name] = get_input_default(field_info, None)
    return defaults


def get_surfaced_prices(
    hub_entry: ConfigEntry,
    element_name: str,
    surfaced_hints: Mapping[str, SurfacedPriceHint],
) -> dict[str, EntityValue | ConstantValue | NoneValue]:
    """Return each surfaced field's stored price, or none when the element has no rule for it."""
    prices: dict[str, EntityValue | ConstantValue | NoneValue] = {}
    for field_name, hint in surfaced_hints.items():
        source, target = resolve_surfaced_endpoints(hint, element_name)
        price = get_surfaced_rule_price(hub_entry, source=source, target=target)
        prices[field_name] = price if price is not None else as_none_value()
    return prices


def build_surfaced_schema_entries(
    hass: HomeAssistant,
    surfaced_fields: Mapping[str, AnyInputFieldInfo],
    entity_metadata: list[EntityMetadata],
) -> dict[str, tuple[vol.Marker, InputSelector]]:
    """Build the schema entries of the surfaced pricing fields."""
    inclusion_map = build_inclusion_map(dict(surfaced_fields), entity_metadata)
    currency = currency_symbol(hass.config.currency)
    return {
        field_name: (
            vol.Optional(field_name),
            build_input_selector(
                localize_input_field(surfaced_field, currency),
                kinds=SURFACED_KINDS,
                entities=inclusion_map[field_name],
            ),
        )
        for field_name, surfaced_field in surfaced_fields.items()
    }


def save_surfaced_rules_from_input(
    hass: HomeAssistant,
    hub_entry: ConfigEntry,
    element_name: str,
    user_input: Mapping[str, object],
    surfaced_hints: dict[str, SurfacedPriceHint],
    translations: Mapping[str, str],
    *,
    apply_defaults: bool = False,
) -> None:
    """Save surfaced policy rules from element config flow input.

    Reads the surfaced price field values from user_input and creates,
    updates, or deletes the corresponding policy rules.

    When apply_defaults is True, fields absent from user_input use the
    hint's default_value, so a new element gets its default rules.
    """
    for field_name, hint in surfaced_hints.items():
        default = hint.hint.default_value
        if field_name in user_input:
            price = form_value_to_price(user_input[field_name])
        elif not apply_defaults:
            continue
        elif isinstance(default, int | float) and not isinstance(default, bool):
            price = as_constant_value(float(default))
        else:
            price = None

        # The form shows the running (positive) value; the policy stores its
        # negative so the optimizer sees the underlying cost.
        if hint.negate:
            price = _negate_price(price)

        source, target = resolve_surfaced_endpoints(hint, element_name)
        rule_name = translations.get(field_name, f"{element_name} {field_name}")
        save_surfaced_rule(
            hass,
            hub_entry,
            rule_name=rule_name,
            source=source,
            target=target,
            price=price,
        )
