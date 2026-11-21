"""Policy element configuration flows.

A single Policies subentry stores every policy rule. Adding a policy and
reconfiguring the policies open the same form, which lists every rule; adding
opens it with a new rule at the end.
"""

from collections.abc import Mapping, Sequence
from typing import Any  # noqa: TID251  # HA flow signatures upstream

from homeassistant.config_entries import ConfigSubentry, SubentryFlowResult
import voluptuous as vol

from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES, ConfiguredRolesAdapter, is_element_type
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.constant_value import as_constant_value, is_constant_value
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.elements.policy import (
    CONF_ENABLED,
    CONF_PRICE,
    CONF_RULES,
    CONF_SOURCE,
    CONF_TARGET,
    ELEMENT_TYPE,
    PolicyRuleConfig,
)
from custom_components.haeo.core.schema.entity_value import is_entity_value
from custom_components.haeo.core.schema.none_value import as_none_value
from custom_components.haeo.core.schema.surfaced_policy import get_surfaced_price_hints, resolve_surfaced_endpoints
from custom_components.haeo.core.units import currency_symbol
from custom_components.haeo.elements import get_list_input_fields
from custom_components.haeo.elements.input_fields import AnyInputFieldInfo, localize_input_field
from custom_components.haeo.flows.connection_selector import ConnectedElement
from custom_components.haeo.flows.element_flow import ElementSubentryFlow, build_inclusion_map
from custom_components.haeo.flows.entity_metadata import extract_entity_metadata
from custom_components.haeo.flows.field_schema import build_input_selector, has_input_value, selector_context
from custom_components.haeo.flows.policy_rules_selector import PolicyRulesSelector, PolicyRuleValue, SurfacedRule
from custom_components.haeo.flows.surfaced_policy import POLICIES_TITLE, find_policy_subentry


def _rule_enabled(rule: PolicyRuleConfig) -> bool:
    """Return whether a stored rule is enabled, from its constant or a bare bool."""
    enabled = rule[CONF_ENABLED]
    return enabled["value"] is True if is_constant_value(enabled) else enabled is True


def _element_roles(element_type: ElementType, config: Mapping[str, object]) -> tuple[bool, bool]:
    """Return whether an element can source and can sink power."""
    adapter = ELEMENT_TYPES[element_type]
    if isinstance(adapter, ConfiguredRolesAdapter):
        return adapter.roles(config)
    return adapter.can_source, adapter.can_sink


def _offers_roles(roles: tuple[bool, bool], *, can_source: bool, can_sink: bool) -> bool:
    """Return whether an element with these roles fits an endpoint needing a source and or a sink."""
    sources, sinks = roles
    return (sources or sinks) and (sources or not can_source) and (sinks or not can_sink)


class PolicySubentryFlowHandler(ElementSubentryFlow):
    """Handle policy element configuration flows."""

    element_type = ELEMENT_TYPE

    def _endpoint_options(self, *, can_source: bool = False, can_sink: bool = False) -> list[ConnectedElement]:
        """Return the elements a rule's end can name: those that can source power, or sink it.

        Whether an element sources or sinks power is its adapter's to declare or,
        for an element choosing its roles in its config, its config's.
        """
        current_id = self._get_current_subentry_id()
        return [
            {"name": subentry.title, "element_type": element_type}
            for subentry in self._get_entry().subentries.values()
            if subentry.subentry_id != current_id
            and is_element_type(element_type := subentry.data.get(CONF_ELEMENT_TYPE))
            and _offers_roles(_element_roles(element_type, subentry.data), can_source=can_source, can_sink=can_sink)
        ]

    def _surfaced_rules(self) -> list[SurfacedRule]:
        """Return the rule patterns elements' own price fields stand for, with the element owning each."""
        surfaced: list[SurfacedRule] = []
        for subentry in self._get_entry().subentries.values():
            for hint in get_surfaced_price_hints(subentry.subentry_type).values():
                source, target = resolve_surfaced_endpoints(hint, subentry.title)
                surfaced.append(
                    {"owner": subentry.title, "owner_type": subentry.subentry_type, "source": source, "target": target}
                )
        return surfaced

    def _target_subentry(self) -> ConfigSubentry | None:
        """Return the single policy subentry, which every rule is saved to."""
        return find_policy_subentry(self._get_entry())

    def _get_price_field_info(self) -> AnyInputFieldInfo:
        """Get the InputFieldInfo for the price field from list field hints."""
        sample: dict[str, object] = {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE,
            CONF_RULES: [{"name": "_", CONF_PRICE: {"type": "constant", "value": 0}}],
        }
        section = next(iter(get_list_input_fields(sample).values()))
        return localize_input_field(section[CONF_PRICE], currency_symbol(self.hass.config.currency))

    def _schema(self) -> vol.Schema:
        """Build the form: every rule, through the rules element."""
        field_info = self._get_price_field_info()
        entity_metadata = extract_entity_metadata(self.hass, self._get_entry())
        price = build_input_selector(
            field_info,
            kinds=("entity", "constant"),
            entities=build_inclusion_map({CONF_PRICE: field_info}, entity_metadata).get(CONF_PRICE),
            context=selector_context(self._get_entry().entry_id, entity_metadata),
        )
        selector = PolicyRulesSelector(
            {
                "sources": self._endpoint_options(can_source=True),
                "targets": self._endpoint_options(can_sink=True),
                "price": price.config,
                "surfaced": self._surfaced_rules(),
            }
        )
        return vol.Schema({vol.Required(CONF_RULES): selector})

    def _stored_rules(self) -> list[PolicyRuleValue]:
        """Return the stored rules as the rules element shows them."""
        subentry = self._target_subentry()
        rules: Sequence[PolicyRuleConfig] = subentry.data.get(CONF_RULES, []) if subentry else []
        return [
            {
                "name": rule["name"],
                "enabled": _rule_enabled(rule),
                "source": list(rule.get(CONF_SOURCE) or []),
                "target": list(rule.get(CONF_TARGET) or []),
                "price": rule[CONF_PRICE],
            }
            for rule in rules
        ]

    @staticmethod
    def _new_rule(rules: Sequence[PolicyRuleValue]) -> PolicyRuleValue:
        """Return a blank rule named apart from the others."""
        names = {rule["name"] for rule in rules}
        number = next(n for n in range(len(rules) + 1, len(rules) + len(names) + 2) if f"Rule {n}" not in names)
        return {"name": f"Rule {number}", "enabled": True, "source": [], "target": [], "price": as_none_value()}

    @staticmethod
    def _validate(rules: Sequence[PolicyRuleValue], errors: dict[str, str]) -> None:
        """Add an error for the first problem with the rules."""
        names = [rule["name"] for rule in rules]
        patterns = [(sorted(rule["source"]), sorted(rule["target"])) for rule in rules]
        for index, rule in enumerate(rules):
            if not rule["name"]:
                errors[CONF_RULES] = "missing_name"
            elif names.count(rule["name"]) > 1:
                errors[CONF_RULES] = "name_exists"
            elif rule["source"] and sorted(rule["source"]) == sorted(rule["target"]):
                errors[CONF_RULES] = "source_target_same"
            elif patterns.index(patterns[index]) != index:
                errors[CONF_RULES] = "duplicate_rule"
            elif not has_input_value(rule["price"]):
                errors[CONF_RULES] = "required"
            if errors:
                return

    @staticmethod
    def _stored_rule(rule: PolicyRuleValue) -> PolicyRuleConfig:
        """Return a validated rule as the policy stores it; an end naming no element is left out."""
        price = rule["price"]
        if not (is_entity_value(price) or is_constant_value(price)):
            msg = "A validated rule has a price"
            raise TypeError(msg)
        stored: PolicyRuleConfig = {
            "name": rule["name"],
            "enabled": as_constant_value(rule["enabled"]),
            "price": price,
        }
        if rule["source"]:
            stored["source"] = rule["source"]
        if rule["target"]:
            stored["target"] = rule["target"]
        return stored

    async def _async_save_rules(
        self, user_input: dict[str, Any] | None, errors: dict[str, str]
    ) -> SubentryFlowResult | None:
        """Save the submitted rules, or add an error and return None when they cannot be saved."""
        if user_input is None:
            return None
        rules: list[PolicyRuleValue] = user_input[CONF_RULES]
        self._validate(rules, errors)
        if errors:
            return None
        return await self._async_save_entry(
            POLICIES_TITLE,
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: POLICIES_TITLE,
                CONF_RULES: [self._stored_rule(rule) for rule in rules],
            },
        )

    def _rules_form(self, user_input: dict[str, Any] | None, *, add_rule: bool) -> vol.Schema:
        """Return the form opening on the submitted rules, or the stored ones with a new rule at the end when adding."""
        if user_input is not None:
            shown: list[PolicyRuleValue] = user_input[CONF_RULES]
        else:
            shown = self._stored_rules()
            if add_rule:
                shown = [*shown, self._new_rule(shown)]
        return self.add_suggested_values_to_schema(self._schema(), {CONF_RULES: shown})

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Show every rule with a new one at the end, creating the Policies subentry for the first."""
        errors: dict[str, str] = {}
        if (saved := await self._async_save_rules(user_input, errors)) is not None:
            return saved
        return self.async_show_form(
            step_id="user", data_schema=self._rules_form(user_input, add_rule=True), errors=errors
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Show every rule to edit, turn on or off, or remove."""
        errors: dict[str, str] = {}
        if (saved := await self._async_save_rules(user_input, errors)) is not None:
            return saved
        return self.async_show_form(
            step_id="reconfigure", data_schema=self._rules_form(user_input, add_rule=False), errors=errors
        )
