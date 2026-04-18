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

from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.constant_value import as_constant_value, is_constant_value
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.elements.node import CONF_IS_SINK, CONF_IS_SOURCE, SECTION_ROLE
from custom_components.haeo.core.schema.elements.node import ELEMENT_TYPE as NODE_ELEMENT_TYPE
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
from custom_components.haeo.core.schema.none_value import is_none_value
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

    def _get_participant_options(
        self,
        *,
        can_source: bool = False,
        can_sink: bool = False,
    ) -> list[str]:
        """Return element names available as policy endpoints.

        Filters by adapter capability: only elements whose adapter declares
        can_source (for source endpoints) or can_sink (for target endpoints)
        are included. For Node elements, additionally checks instance-specific
        role flags from the subentry data.
        """
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

            adapter = ELEMENT_TYPES.get(element_type)
            if adapter is None:
                continue

            if not adapter.can_source and not adapter.can_sink:
                continue

            # Node elements have instance-specific capabilities via role flags
            if element_type == NODE_ELEMENT_TYPE:
                role = subentry.data.get(SECTION_ROLE, {})
                node_can_source = role.get(CONF_IS_SOURCE, False)
                node_can_sink = role.get(CONF_IS_SINK, False)
                if can_source and not node_can_source:
                    continue
                if can_sink and not node_can_sink:
                    continue
                if not node_can_source and not node_can_sink:
                    continue
            else:
                if can_source and not adapter.can_source:
                    continue
                if can_sink and not adapter.can_sink:
                    continue

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
        """Build a ChooseSelector for the price field (entity/constant)."""
        field_info = self._get_price_field_info()
        return build_choose_selector(
            field_info,
            allowed_choices={CHOICE_ENTITY, CHOICE_CONSTANT},
            multiple=True,
            preferred_choice=CHOICE_CONSTANT,
        )

    def _build_endpoint_selector(
        self,
        participants: list[str],
        *,
        preferred_choice: str = CHOICE_NONE,
    ) -> _EndpointChooseSelector:
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
        choice_map = {
            CHOICE_NONE: ChooseSelectorChoiceConfig(
                selector=none_selector.serialize()["selector"],
            ),
            CHOICE_ELEMENTS: ChooseSelectorChoiceConfig(
                selector=elements_selector.serialize()["selector"],
            ),
        }
        choice_order = [CHOICE_NONE, CHOICE_ELEMENTS]
        if preferred_choice in choice_order:
            choice_order.remove(preferred_choice)
            choice_order.insert(0, preferred_choice)

        return _EndpointChooseSelector(
            ChooseSelectorConfig(
                choices={k: choice_map[k] for k in choice_order},
                translation_key="policy_endpoint",
            )
        )

    def _get_preferred_endpoint_choice(self, value: Any) -> str:
        """Return endpoint choice key to place first in selector ordering."""
        if isinstance(value, dict) and value.get("active_choice") == CHOICE_ELEMENTS:
            return CHOICE_ELEMENTS
        if isinstance(value, list) and value:
            return CHOICE_ELEMENTS
        return CHOICE_NONE

    def _build_rule_schema(
        self,
        source_options: list[str],
        target_options: list[str],
        *,
        source_preferred_choice: str = CHOICE_NONE,
        target_preferred_choice: str = CHOICE_NONE,
    ) -> vol.Schema:
        """Build the schema for adding or editing a policy rule."""
        source_selector = self._build_endpoint_selector(
            source_options,
            preferred_choice=source_preferred_choice,
        )
        target_selector = self._build_endpoint_selector(
            target_options,
            preferred_choice=target_preferred_choice,
        )
        price_selector = self._build_price_selector()

        return vol.Schema(
            {
                vol.Required(CONF_RULE_NAME): str,
                vol.Required(CONF_ENABLED, default=True): BooleanSelector(BooleanSelectorConfig()),
                vol.Optional(CONF_SOURCE): source_selector,
                vol.Optional(CONF_TARGET): target_selector,
                vol.Required(CONF_PRICE): price_selector,
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
        defaults[CONF_SOURCE] = source if source else ""

        target = rule.get(CONF_TARGET)
        defaults[CONF_TARGET] = target if target else ""

        if CONF_PRICE in rule:
            price = rule[CONF_PRICE]
            if is_constant_value(price) or is_entity_value(price):
                defaults[CONF_PRICE] = price["value"]
        return defaults

    def _rule_to_edit_input(self, rule: PolicyRuleConfig) -> dict[str, Any]:
        """Convert a stored rule into parse-ready form input values."""
        input_values: dict[str, Any] = {
            CONF_RULE_NAME: rule["name"],
            CONF_ENABLED: rule.get(CONF_ENABLED, True),
            CONF_SOURCE: rule.get(CONF_SOURCE, ""),
            CONF_TARGET: rule.get(CONF_TARGET, ""),
        }

        if CONF_PRICE in rule:
            price = rule[CONF_PRICE]
            if is_constant_value(price) or is_entity_value(price):
                input_values[CONF_PRICE] = price["value"]
            elif is_none_value(price):
                input_values[CONF_PRICE] = ""

        return input_values

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

        price = user_input.get(CONF_PRICE)
        if isinstance(price, str) and price == "":
            errors[CONF_PRICE] = "required"
            return False
        if price is None:
            errors[CONF_PRICE] = "required"
            return False
        if isinstance(price, list) and not price:
            errors[CONF_PRICE] = "required"
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
        source_options = self._get_participant_options(can_source=True)
        target_options = self._get_participant_options(can_sink=True)

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

        source_preferred_choice = CHOICE_NONE
        target_preferred_choice = CHOICE_NONE
        if user_input is not None:
            source_preferred_choice = self._get_preferred_endpoint_choice(user_input.get(CONF_SOURCE))
            target_preferred_choice = self._get_preferred_endpoint_choice(user_input.get(CONF_TARGET))

        schema = self._build_rule_schema(
            source_options,
            target_options,
            source_preferred_choice=source_preferred_choice,
            target_preferred_choice=target_preferred_choice,
        )
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
        source_options = self._get_participant_options(can_source=True)
        target_options = self._get_participant_options(can_sink=True)
        idx = self._editing_index
        existing_rule_input: dict[str, Any] = {}
        if idx is not None and 0 <= idx < len(self._rules):
            existing_rule_input = self._rule_to_edit_input(self._rules[idx])

        merged_input = {**existing_rule_input, **user_input} if user_input is not None else None

        if merged_input is not None and self._validate_rule(
            merged_input,
            errors,
            exclude_index=idx,
        ):
            rule = self._parse_rule_input(merged_input)
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

        if merged_input is not None:
            defaults = merged_input
        elif idx is not None and 0 <= idx < len(self._rules):
            defaults = self._rule_to_defaults(self._rules[idx])
        else:
            defaults = {}
        source_preferred_choice = self._get_preferred_endpoint_choice(defaults.get(CONF_SOURCE))
        target_preferred_choice = self._get_preferred_endpoint_choice(defaults.get(CONF_TARGET))
        schema = self._build_rule_schema(
            source_options,
            target_options,
            source_preferred_choice=source_preferred_choice,
            target_preferred_choice=target_preferred_choice,
        )
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="edit_rule",
            data_schema=schema,
            errors=errors,
        )
