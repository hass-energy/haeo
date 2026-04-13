"""Policy element configuration flows.

A single Policies subentry stores multiple policy rules.
The flow uses a menu-driven pattern:
- New subentry: adds the first rule, then creates the entry.
- Reconfigure: shows a menu of existing rules with add/save options.
"""

from typing import Any

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers.selector import (
    BooleanSelector,
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
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
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
CONF_DELETE: str = "delete"
ACTION_ADD: str = "add"
ACTION_DONE: str = "done"

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

            # Policies can target any model element except other policies and connections
            if element_type not in (ElementType.POLICY, ElementType.CONNECTION):
                result.append(subentry.title)

        return result

    def _build_rule_schema(
        self,
        participants: list[str],
        *,
        is_edit: bool = False,
    ) -> vol.Schema:
        """Build the schema for adding or editing a policy rule."""
        source_options = [WILDCARD, *participants]
        target_options = [WILDCARD, *participants]

        schema: dict[vol.Marker, Any] = {
            vol.Required(CONF_RULE_NAME): str,
            vol.Required(CONF_SOURCE): SelectSelector(
                SelectSelectorConfig(
                    options=source_options,
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="policy_endpoint",
                )
            ),
            vol.Required(CONF_TARGET): SelectSelector(
                SelectSelectorConfig(
                    options=target_options,
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="policy_endpoint",
                )
            ),
            vol.Optional(CONF_PRICE_SOURCE_TARGET): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=0.001,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="$/kWh",
                )
            ),
            vol.Optional(CONF_PRICE_TARGET_SOURCE): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=0.001,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="$/kWh",
                )
            ),
        }

        if is_edit:
            schema[vol.Optional(CONF_DELETE, default=False)] = BooleanSelector()

        return vol.Schema(schema)

    def _build_menu_schema(self) -> vol.Schema:
        """Build the schema for the rule selection menu."""
        options: list[SelectOptionDict] = [
            *[SelectOptionDict(value=str(i), label=rule["name"]) for i, rule in enumerate(self._rules)],
            SelectOptionDict(value=ACTION_ADD, label="Add new policy"),
            SelectOptionDict(value=ACTION_DONE, label="Save and close"),
        ]
        return vol.Schema(
            {
                vol.Required(CONF_ACTION): SelectSelector(
                    SelectSelectorConfig(
                        options=options,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
            }
        )

    def _parse_rule_input(self, user_input: dict[str, Any]) -> PolicyRuleConfig:
        """Convert form input into a PolicyRuleConfig."""
        rule: PolicyRuleConfig = {
            "name": user_input[CONF_RULE_NAME],
            "source": user_input[CONF_SOURCE],
            "target": user_input[CONF_TARGET],
        }
        if (price_st := user_input.get(CONF_PRICE_SOURCE_TARGET)) is not None:
            rule["price_source_target"] = float(price_st)
        if (price_ts := user_input.get(CONF_PRICE_TARGET_SOURCE)) is not None:
            rule["price_target_source"] = float(price_ts)
        return rule

    def _rule_to_defaults(self, rule: PolicyRuleConfig) -> dict[str, Any]:
        """Convert a stored rule back to form defaults."""
        defaults: dict[str, Any] = {
            CONF_RULE_NAME: rule["name"],
            CONF_SOURCE: rule["source"],
            CONF_TARGET: rule["target"],
        }
        if "price_source_target" in rule:
            defaults[CONF_PRICE_SOURCE_TARGET] = rule["price_source_target"]
        if "price_target_source" in rule:
            defaults[CONF_PRICE_TARGET_SOURCE] = rule["price_target_source"]
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

        source = user_input.get(CONF_SOURCE)
        target = user_input.get(CONF_TARGET)
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
        """Handle adding the Policies subentry with the first rule."""
        errors: dict[str, str] = {}
        participants = self._get_participant_options()

        if user_input is not None and self._validate_rule(user_input, errors):
            rule = self._parse_rule_input(user_input)
            self._rules = [rule]
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
        """Handle opening the policy menu for an existing subentry."""
        subentry = self._get_subentry()
        if subentry is not None and not self._rules:
            self._rules = list(subentry.data.get(CONF_RULES, []))
        return await self.async_step_menu(user_input)

    async def async_step_menu(
        self, user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Show the policy rule menu."""
        if user_input is not None:
            action = user_input.get(CONF_ACTION, "")

            if action == ACTION_ADD:
                return await self.async_step_add_rule()

            if action == ACTION_DONE:
                subentry = self._get_subentry()
                if subentry is not None:
                    return self.async_update_and_abort(
                        self._get_entry(),
                        subentry,
                        title=POLICIES_TITLE,
                        data=self._build_entry_data(),
                    )
                return self.async_create_entry(
                    title=POLICIES_TITLE,
                    data=self._build_entry_data(),
                )

            # Numeric action = edit a specific rule
            if action.isdigit():
                self._editing_index = int(action)
                return await self.async_step_edit_rule()

        schema = self._build_menu_schema()
        return self.async_show_form(
            step_id="menu",
            data_schema=schema,
        )

    async def async_step_add_rule(
        self, user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Handle adding a new policy rule."""
        errors: dict[str, str] = {}
        participants = self._get_participant_options()

        if user_input is not None and self._validate_rule(user_input, errors):
            rule = self._parse_rule_input(user_input)
            self._rules.append(rule)
            return await self.async_step_menu()

        schema = self._build_rule_schema(participants)
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)

        return self.async_show_form(
            step_id="add_rule",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_edit_rule(
        self, user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Handle editing or deleting an existing policy rule."""
        errors: dict[str, str] = {}
        participants = self._get_participant_options()
        idx = self._editing_index

        if user_input is not None:
            if user_input.get(CONF_DELETE):
                if idx is not None and 0 <= idx < len(self._rules):
                    self._rules.pop(idx)
                self._editing_index = None
                return await self.async_step_menu()

            if self._validate_rule(user_input, errors, exclude_index=idx):
                rule = self._parse_rule_input(user_input)
                if idx is not None and 0 <= idx < len(self._rules):
                    self._rules[idx] = rule
                self._editing_index = None
                return await self.async_step_menu()

        schema = self._build_rule_schema(participants, is_edit=True)
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
