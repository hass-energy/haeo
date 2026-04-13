"""Policy element configuration flows.

A single Policies subentry stores multiple policy rules.

Flow design:
- async_step_user: Adds a new rule. If a Policies subentry already exists,
  appends to it; otherwise creates one.
- async_step_reconfigure: Shows existing rules for edit or delete.
- async_step_edit_rule: Edits a selected rule.
"""

from typing import Any

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
import voluptuous as vol

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.elements.policy import (
    CONF_PRICE,
    CONF_RULE_NAME,
    CONF_RULES,
    CONF_SOURCE,
    CONF_TARGET,
    ELEMENT_TYPE,
    WILDCARD,
    PolicyRuleConfig,
)
from custom_components.haeo.flows.element_flow import ElementFlowMixin

CONF_ACTION: str = "action"
CONF_RULE: str = "rule"
ACTION_EDIT: str = "edit"
ACTION_DELETE: str = "delete"

POLICIES_TITLE: str = "Policies"


class PolicySubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle policy element configuration flows."""

    def __init__(self) -> None:
        """Initialize the policy flow handler."""
        super().__init__()
        self._rules: list[PolicyRuleConfig] = []
        self._editing_index: int | None = None

    def _get_participant_options(self) -> list[str]:
        """Return all element names available as policy endpoints.

        Unlike connection flows that filter by connectivity, policies can
        reference any element that participates in the model. This includes
        all element types except other policies and connections.
        """
        from custom_components.haeo.core.schema.elements import ElementType  # noqa: PLC0415

        hub_entry = self._get_entry()
        current_id = self._get_current_subentry_id()

        result: list[str] = []
        for subentry in hub_entry.subentries.values():
            if subentry.subentry_id == current_id:
                continue

            element_type = subentry.data.get(CONF_ELEMENT_TYPE)
            if not isinstance(element_type, ElementType):
                continue

            if element_type not in (ElementType.POLICY, ElementType.CONNECTION):
                result.append(subentry.title)

        return result

    def _find_existing_policy_subentry(self) -> Any | None:
        """Find the existing Policies subentry if one exists."""
        hub_entry = self._get_entry()
        for subentry in hub_entry.subentries.values():
            if subentry.subentry_type == str(ELEMENT_TYPE):
                return subentry
        return None

    def _build_rule_schema(self, participants: list[str]) -> vol.Schema:
        """Build the schema for adding or editing a policy rule."""
        source_options = [
            SelectOptionDict(value=WILDCARD, label="None"),
            *[SelectOptionDict(value=p, label=p) for p in participants],
        ]
        target_options = [
            SelectOptionDict(value=WILDCARD, label="None"),
            *[SelectOptionDict(value=p, label=p) for p in participants],
        ]

        return vol.Schema({
            vol.Required(CONF_RULE_NAME): str,
            vol.Optional(CONF_SOURCE, default=WILDCARD): SelectSelector(
                SelectSelectorConfig(
                    options=source_options,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_TARGET, default=WILDCARD): SelectSelector(
                SelectSelectorConfig(
                    options=target_options,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_PRICE): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=0.001,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="$/kWh",
                )
            ),
        })

    def _build_reconfigure_schema(self) -> vol.Schema:
        """Build the schema for the reconfigure menu."""
        rule_options: list[SelectOptionDict] = [
            SelectOptionDict(value=str(i), label=rule["name"])
            for i, rule in enumerate(self._rules)
        ]
        action_options: list[SelectOptionDict] = [
            SelectOptionDict(value=ACTION_EDIT, label="Edit"),
            SelectOptionDict(value=ACTION_DELETE, label="Delete"),
        ]
        return vol.Schema({
            vol.Required(CONF_RULE): SelectSelector(
                SelectSelectorConfig(
                    options=rule_options,
                    mode=SelectSelectorMode.LIST,
                )
            ),
            vol.Required(CONF_ACTION): SelectSelector(
                SelectSelectorConfig(
                    options=action_options,
                    mode=SelectSelectorMode.LIST,
                )
            ),
        })

    def _parse_rule_input(self, user_input: dict[str, Any]) -> PolicyRuleConfig:
        """Convert form input into a PolicyRuleConfig."""
        rule: PolicyRuleConfig = {"name": user_input[CONF_RULE_NAME]}
        source = user_input.get(CONF_SOURCE, WILDCARD)
        target = user_input.get(CONF_TARGET, WILDCARD)
        if source != WILDCARD:
            rule["source"] = source
        if target != WILDCARD:
            rule["target"] = target
        if (price := user_input.get(CONF_PRICE)) is not None:
            rule["price"] = float(price)
        return rule

    def _rule_to_defaults(self, rule: PolicyRuleConfig) -> dict[str, Any]:
        """Convert a stored rule back to form defaults."""
        defaults: dict[str, Any] = {
            CONF_RULE_NAME: rule["name"],
            CONF_SOURCE: rule.get("source", WILDCARD),
            CONF_TARGET: rule.get("target", WILDCARD),
        }
        if "price" in rule:
            defaults[CONF_PRICE] = rule["price"]
        return defaults

    def _validate_rule(
        self,
        user_input: dict[str, Any],
        errors: dict[str, str],
        *,
        exclude_index: int | None = None,
    ) -> bool:
        """Validate a rule's fields. Returns True if valid."""
        name = user_input.get(CONF_RULE_NAME)
        if not name:
            errors[CONF_RULE_NAME] = "missing_name"
            return False

        existing_names = {
            rule["name"]
            for i, rule in enumerate(self._rules)
            if i != exclude_index
        }
        if name in existing_names:
            errors[CONF_RULE_NAME] = "name_exists"
            return False

        source = user_input.get(CONF_SOURCE, WILDCARD)
        target = user_input.get(CONF_TARGET, WILDCARD)
        if source == target and source != WILDCARD:
            errors["base"] = "source_target_same"
            return False

        return True

    def _build_entry_data(self) -> dict[str, Any]:
        """Build the subentry data dict from accumulated rules."""
        return {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE,
            CONF_NAME: POLICIES_TITLE,
            CONF_RULES: list(self._rules),
        }

    # --- Flow steps ---

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Handle adding a new policy rule.

        If a Policies subentry already exists, appends the rule to it.
        Otherwise creates a new Policies subentry.
        """
        errors: dict[str, str] = {}
        participants = self._get_participant_options()

        if user_input is not None:
            existing = self._find_existing_policy_subentry()
            if existing is not None and not self._rules:
                self._rules = list(existing.data.get(CONF_RULES, []))

            if self._validate_rule(user_input, errors):
                rule = self._parse_rule_input(user_input)
                self._rules.append(rule)

                if existing is not None:
                    return self.async_update_and_abort(
                        self._get_entry(),
                        existing,
                        title=POLICIES_TITLE,
                        data=self._build_entry_data(),
                    )
                return self.async_create_entry(
                    title=POLICIES_TITLE,
                    data=self._build_entry_data(),
                )

        schema = self._build_rule_schema(participants)
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Handle the reconfigure menu for managing existing rules."""
        subentry = self._get_subentry()
        if subentry is not None and not self._rules:
            self._rules = list(subentry.data.get(CONF_RULES, []))

        if not self._rules:
            return self.async_abort(reason="no_rules")

        if user_input is not None:
            rule_index = int(user_input[CONF_RULE])
            action = user_input[CONF_ACTION]

            if action == ACTION_DELETE:
                if 0 <= rule_index < len(self._rules):
                    self._rules.pop(rule_index)
                if subentry is not None:
                    return self.async_update_and_abort(
                        self._get_entry(),
                        subentry,
                        title=POLICIES_TITLE,
                        data=self._build_entry_data(),
                    )

            if action == ACTION_EDIT and 0 <= rule_index < len(self._rules):
                self._editing_index = rule_index
                return await self.async_step_edit_rule()

        schema = self._build_reconfigure_schema()
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
        )

    async def async_step_edit_rule(
        self, user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Handle editing an existing policy rule."""
        errors: dict[str, str] = {}
        participants = self._get_participant_options()
        idx = self._editing_index

        if user_input is not None and self._validate_rule(
            user_input, errors, exclude_index=idx,
        ):
            rule = self._parse_rule_input(user_input)
            if idx is not None and 0 <= idx < len(self._rules):
                self._rules[idx] = rule
            self._editing_index = None

            subentry = self._get_subentry()
            if subentry is not None:
                return self.async_update_and_abort(
                    self._get_entry(),
                    subentry,
                    title=POLICIES_TITLE,
                    data=self._build_entry_data(),
                )

        schema = self._build_rule_schema(participants)
        if user_input is not None:
            defaults = user_input
        elif idx is not None and 0 <= idx < len(self._rules):
            defaults = self._rule_to_defaults(self._rules[idx])
        else:
            defaults = {}
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="edit_rule",
            data_schema=schema,
            errors=errors,
        )
