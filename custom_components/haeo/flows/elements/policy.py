"""Policy element configuration flows.

A single Policies subentry stores multiple policy rules.

Flow design:
- async_step_user: Adds a new rule. If a Policies subentry already exists,
  appends to it; otherwise creates one.
- async_step_reconfigure: Shows existing rules for edit or delete.
- async_step_edit_rule: Edits a selected rule.
"""

from typing import Any

from homeassistant.config_entries import ConfigSubentry, ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    ChooseSelector,
    ChooseSelectorChoiceConfig,
    ChooseSelectorConfig,
    ConstantSelector,
    ConstantSelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
import voluptuous as vol

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.constant_value import as_constant_value, is_constant_value
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.elements.policy import (
    CONF_ENABLED,
    CONF_PRICE,
    CONF_RULE_NAME,
    CONF_RULES,
    CONF_SOURCE,
    CONF_TARGET,
    ELEMENT_TYPE,
    PolicyRuleConfig,
)
from custom_components.haeo.core.schema.entity_value import as_entity_value, is_entity_value
from custom_components.haeo.core.schema.none_value import as_none_value, is_none_value
from custom_components.haeo.elements import get_list_input_fields
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.flows.element_flow import ElementFlowMixin
from custom_components.haeo.flows.field_schema import (
    CHOICE_CONSTANT,
    CHOICE_ENTITY,
    CHOICE_NONE,
    NormalizingChooseSelector,
    build_choose_selector,
)

CONF_ACTION: str = "action"
CONF_RULE: str = "rule"
ACTION_EDIT: str = "edit"
ACTION_DELETE: str = "delete"

CHOICE_ELEMENTS: str = "elements"

POLICIES_TITLE: str = "Policies"


class _EndpointChooseSelector(ChooseSelector):  # type: ignore[type-arg]
    """ChooseSelector for policy endpoints that normalizes to list[str] or empty.

    - "none" choice (any element): normalizes to empty string
    - "elements" choice (specific elements): normalizes to list[str]
    """

    def __call__(self, data: Any) -> Any:
        """Normalize endpoint data before validation."""
        if isinstance(data, dict) and "active_choice" in data:
            choice = data.get("active_choice")
            if choice == CHOICE_NONE:
                return ""
            if choice == CHOICE_ELEMENTS:
                elements = data.get(CHOICE_ELEMENTS, [])
                if not elements:
                    msg = "At least one element must be selected"
                    raise vol.Invalid(msg)
                return elements
        return super().__call__(data)  # type: ignore[misc]


class PolicySubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle policy element configuration flows."""

    def __init__(self) -> None:
        """Initialize the policy flow handler."""
        super().__init__()
        self._rules: list[PolicyRuleConfig] = []
        self._editing_index: int | None = None

    def _get_participant_options(self) -> list[str]:
        """Return all element names available as policy endpoints."""
        hub_entry = self._get_entry()
        current_id = self._get_current_subentry_id()

        result: list[str] = []
        for subentry in hub_entry.subentries.values():
            if subentry.subentry_id == current_id:
                continue

            try:
                element_type = ElementType(subentry.data.get(CONF_ELEMENT_TYPE))
            except (ValueError, KeyError):
                continue

            if element_type not in (ElementType.POLICY, ElementType.CONNECTION):
                result.append(subentry.title)

        return result

    def _find_existing_policy_subentry(self) -> ConfigSubentry | None:
        """Find the existing Policies subentry if one exists."""
        hub_entry = self._get_entry()
        for subentry in hub_entry.subentries.values():
            if subentry.subentry_type == str(ELEMENT_TYPE):
                return subentry
        return None

    def _get_price_field_info(self) -> InputFieldInfo[Any]:
        """Get the InputFieldInfo for the price field from list field hints."""
        dummy_config: dict[str, Any] = {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE,
            CONF_RULES: [{"name": "_", CONF_PRICE: {"type": "constant", "value": 0}}],
        }
        list_fields = get_list_input_fields(dummy_config)
        section = next(iter(list_fields.values()))
        return section[CONF_PRICE]

    def _build_price_selector(self) -> NormalizingChooseSelector:
        """Build a ChooseSelector for the price field (entity/constant/none)."""
        field_info = self._get_price_field_info()
        return build_choose_selector(
            field_info,
            allowed_choices={CHOICE_ENTITY, CHOICE_CONSTANT, CHOICE_NONE},
            multiple=True,
            preferred_choice=CHOICE_CONSTANT,
        )

    def _build_endpoint_selector(self, participants: list[str]) -> _EndpointChooseSelector:
        """Build a ChooseSelector for endpoint with none (any) and elements (specific) choices."""
        options = [SelectOptionDict(value=p, label=p) for p in participants]
        elements_selector = SelectSelector(
            SelectSelectorConfig(
                options=options,
                mode=SelectSelectorMode.DROPDOWN,
                multiple=True,
            )
        )
        none_selector = ConstantSelector(ConstantSelectorConfig(value=""))
        return _EndpointChooseSelector(
            ChooseSelectorConfig(
                choices={
                    CHOICE_NONE: ChooseSelectorChoiceConfig(
                        selector=none_selector.serialize()["selector"],
                    ),
                    CHOICE_ELEMENTS: ChooseSelectorChoiceConfig(
                        selector=elements_selector.serialize()["selector"],
                    ),
                },
                translation_key="policy_endpoint",
            )
        )

    def _build_rule_schema(self, participants: list[str]) -> vol.Schema:
        """Build the schema for adding or editing a policy rule."""
        endpoint_selector = self._build_endpoint_selector(participants)
        price_selector = self._build_price_selector()

        return vol.Schema(
            {
                vol.Required(CONF_RULE_NAME): str,
                vol.Required(CONF_ENABLED, default=True): BooleanSelector(BooleanSelectorConfig()),
                vol.Optional(CONF_SOURCE): endpoint_selector,
                vol.Optional(CONF_TARGET): endpoint_selector,
                vol.Optional(CONF_PRICE): price_selector,
            }
        )

    def _build_reconfigure_schema(self) -> vol.Schema:
        """Build the schema for the reconfigure menu."""
        rule_options: list[SelectOptionDict] = [
            SelectOptionDict(value=str(i), label=rule["name"]) for i, rule in enumerate(self._rules)
        ]
        action_options: list[SelectOptionDict] = [
            SelectOptionDict(value=ACTION_EDIT, label="Edit"),
            SelectOptionDict(value=ACTION_DELETE, label="Delete"),
        ]
        return vol.Schema(
            {
                vol.Required(CONF_RULE): SelectSelector(
                    SelectSelectorConfig(
                        options=rule_options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_ACTION): SelectSelector(
                    SelectSelectorConfig(
                        options=action_options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

    def _parse_rule_input(self, user_input: dict[str, Any]) -> PolicyRuleConfig:
        """Convert form input into a PolicyRuleConfig."""
        rule: PolicyRuleConfig = {"name": user_input[CONF_RULE_NAME]}
        rule["enabled"] = user_input[CONF_ENABLED]

        source = user_input.get(CONF_SOURCE)
        if isinstance(source, list) and source:
            rule["source"] = source

        target = user_input.get(CONF_TARGET)
        if isinstance(target, list) and target:
            rule["target"] = target

        price = user_input.get(CONF_PRICE)
        if price is not None:
            if isinstance(price, list):
                rule["price"] = as_entity_value(price)
            elif isinstance(price, str) and price == "":
                rule["price"] = as_none_value()
            elif isinstance(price, (int, float)):
                rule["price"] = as_constant_value(float(price))
        return rule

    def _rule_to_defaults(self, rule: PolicyRuleConfig) -> dict[str, Any]:
        """Convert a stored rule back to form defaults."""
        defaults: dict[str, Any] = {
            CONF_RULE_NAME: rule["name"],
            CONF_ENABLED: rule.get(CONF_ENABLED, True),
        }

        source = rule.get(CONF_SOURCE)
        defaults[CONF_SOURCE] = {"active_choice": CHOICE_ELEMENTS, CHOICE_ELEMENTS: source} if source else ""

        target = rule.get(CONF_TARGET)
        defaults[CONF_TARGET] = {"active_choice": CHOICE_ELEMENTS, CHOICE_ELEMENTS: target} if target else ""

        if CONF_PRICE in rule:
            price = rule[CONF_PRICE]
            if is_constant_value(price) or is_entity_value(price):
                defaults[CONF_PRICE] = price["value"]
            elif is_none_value(price):
                defaults[CONF_PRICE] = ""
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

        existing_names = {rule["name"] for i, rule in enumerate(self._rules) if i != exclude_index}
        if name in existing_names:
            errors[CONF_RULE_NAME] = "name_exists"
            return False

        source = user_input.get(CONF_SOURCE) or []
        target = user_input.get(CONF_TARGET) or []
        if source and target and source == target:
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
        self,
        user_input: dict[str, Any] | None = None,
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
        self,
        user_input: dict[str, Any] | None = None,
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
        self,
        user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Handle editing an existing policy rule."""
        errors: dict[str, str] = {}
        participants = self._get_participant_options()
        idx = self._editing_index

        if user_input is not None and self._validate_rule(
            user_input,
            errors,
            exclude_index=idx,
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
