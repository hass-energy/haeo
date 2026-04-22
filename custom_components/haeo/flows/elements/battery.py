"""Battery element configuration flows.

Flow design:
- async_step_user: Main battery config (storage, power limits, pricing, efficiency).
- async_step_reconfigure: Also routes to inventory cost management via menu.
- async_step_add_inventory_cost: Adds a new inventory cost rule.
- async_step_manage_inventory_costs: Edit/delete existing inventory cost rules.
- async_step_edit_inventory_cost: Edits a selected inventory cost rule.
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
from custom_components.haeo.core.schema import get_connection_target_name, normalize_connection_target
from custom_components.haeo.core.schema.constant_value import as_constant_value, is_constant_value
from custom_components.haeo.core.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_COST,
    CONF_COST_NAME,
    CONF_DIRECTION,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_INVENTORY_COSTS,
    CONF_SALVAGE_VALUE,
    CONF_THRESHOLD,
    ELEMENT_TYPE,
    SECTION_STORAGE,
    InventoryCostConfig,
)
from custom_components.haeo.core.schema.entity_value import as_entity_value, is_entity_value
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
)
from custom_components.haeo.elements import get_input_field_schema_info, get_input_fields
from custom_components.haeo.elements.input_fields import InputFieldGroups
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_sectioned_inclusion_map
from custom_components.haeo.flows.entity_metadata import extract_entity_metadata
from custom_components.haeo.flows.field_schema import (
    SectionDefinition,
    build_sectioned_choose_defaults,
    build_sectioned_choose_schema,
    convert_sectioned_choose_data_to_config,
    preprocess_sectioned_choose_input,
    validate_sectioned_choose_fields,
)
from custom_components.haeo.sections import (
    build_common_fields,
    efficiency_section,
    power_limits_section,
    pricing_section,
)

CONF_ACTION: str = "action"
CONF_COST_RULE: str = "cost_rule"
ACTION_EDIT: str = "edit"
ACTION_DELETE: str = "delete"
ACTION_ADD_INVENTORY_COST: str = "add_inventory_cost"

DIRECTION_ABOVE: str = "above"
DIRECTION_BELOW: str = "below"


class BatterySubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle battery element configuration flows."""

    def __init__(self) -> None:
        """Initialize the flow handler."""
        super().__init__()
        self._step1_data: dict[str, Any] = {}
        self._inventory_costs: list[InventoryCostConfig] = []
        self._editing_index: int | None = None

    def _get_sections(self) -> tuple[SectionDefinition, ...]:
        """Return sections for the main configuration step."""
        return (
            SectionDefinition(
                key=SECTION_STORAGE, fields=(CONF_CAPACITY, CONF_INITIAL_CHARGE_PERCENTAGE), collapsed=False
            ),
            power_limits_section((CONF_MAX_POWER_TARGET_SOURCE, CONF_MAX_POWER_SOURCE_TARGET), collapsed=False),
            pricing_section((CONF_SALVAGE_VALUE,), collapsed=False),
            efficiency_section((CONF_EFFICIENCY_SOURCE_TARGET, CONF_EFFICIENCY_TARGET_SOURCE), collapsed=True),
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle user step: name, connection, and input configuration."""
        return await self._async_step_user(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step: name, connection, and input configuration."""
        return await self._async_step_user(user_input)

    async def _async_step_user(self, user_input: dict[str, Any] | None) -> SubentryFlowResult:
        """Shared logic for user and reconfigure steps."""
        subentry = self._get_subentry()
        subentry_data = dict(subentry.data) if subentry else None
        participants = self._get_participant_names()
        current_connection = get_connection_target_name(subentry_data.get(CONF_CONNECTION)) if subentry_data else None
        default_name = await self._async_get_default_name(ELEMENT_TYPE)
        if not isinstance(current_connection, str):
            current_connection = participants[0] if participants else ""

        input_fields = get_input_fields(ELEMENT_TYPE)

        sections = self._get_sections()
        user_input = preprocess_sectioned_choose_input(user_input, input_fields, sections)
        errors = self._validate_user_input(user_input, input_fields)

        if user_input is not None and not errors:
            self._step1_data = user_input
            # Load existing inventory costs if reconfiguring
            if subentry_data and not self._inventory_costs:
                self._inventory_costs = list(subentry_data.get(CONF_INVENTORY_COSTS, []))
            config = self._build_config(user_input)
            return self._finalize(config)

        entity_metadata = extract_entity_metadata(self.hass)
        section_inclusion_map = build_sectioned_inclusion_map(input_fields, entity_metadata)
        schema = self._build_schema(
            participants,
            input_fields,
            section_inclusion_map,
            current_connection,
            subentry_data,
        )
        defaults = (
            user_input
            if user_input is not None
            else self._build_defaults(
                default_name,
                input_fields,
                subentry_data,
                current_connection,
            )
        )
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    # --- Inventory cost management steps ---

    async def async_step_add_inventory_cost(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Handle adding a new inventory cost rule."""
        errors: dict[str, str] = {}
        subentry = self._get_subentry()
        subentry_data = dict(subentry.data) if subentry else None

        if subentry_data is not None and not self._inventory_costs:
            self._inventory_costs = list(subentry_data.get(CONF_INVENTORY_COSTS, []))

        if user_input is not None:
            if self._validate_cost_rule(user_input, errors):
                rule = self._parse_cost_input(user_input)
                self._inventory_costs.append(rule)
                if subentry is not None:
                    return self._update_inventory_costs(subentry_data)
                return self.async_abort(reason="no_subentry")

        schema = self._build_cost_rule_schema()
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)

        return self.async_show_form(
            step_id="add_inventory_cost",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_manage_inventory_costs(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Handle the management menu for existing inventory cost rules."""
        subentry = self._get_subentry()
        subentry_data = dict(subentry.data) if subentry else None
        if subentry_data is not None and not self._inventory_costs:
            self._inventory_costs = list(subentry_data.get(CONF_INVENTORY_COSTS, []))

        if not self._inventory_costs:
            return self.async_abort(reason="no_inventory_costs")

        if user_input is not None:
            rule_index = int(user_input[CONF_COST_RULE])
            action = user_input[CONF_ACTION]

            if action == ACTION_DELETE:
                if 0 <= rule_index < len(self._inventory_costs):
                    self._inventory_costs.pop(rule_index)
                if subentry_data is not None:
                    return self._update_inventory_costs(subentry_data)

            if action == ACTION_EDIT and 0 <= rule_index < len(self._inventory_costs):
                self._editing_index = rule_index
                return await self.async_step_edit_inventory_cost()

        schema = self._build_manage_costs_schema()
        return self.async_show_form(
            step_id="manage_inventory_costs",
            data_schema=schema,
        )

    async def async_step_edit_inventory_cost(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Handle editing an existing inventory cost rule."""
        errors: dict[str, str] = {}
        idx = self._editing_index
        existing_rule_input: dict[str, Any] = {}
        if idx is not None and 0 <= idx < len(self._inventory_costs):
            existing_rule_input = self._cost_to_edit_input(self._inventory_costs[idx])

        merged_input = {**existing_rule_input, **user_input} if user_input is not None else None

        if merged_input is not None and self._validate_cost_rule(
            merged_input,
            errors,
            exclude_index=idx,
        ):
            rule = self._parse_cost_input(merged_input)
            if idx is not None and 0 <= idx < len(self._inventory_costs):
                self._inventory_costs[idx] = rule
            self._editing_index = None

            subentry = self._get_subentry()
            subentry_data = dict(subentry.data) if subentry else None
            if subentry_data is not None:
                return self._update_inventory_costs(subentry_data)

        if merged_input is not None:
            defaults = merged_input
        elif idx is not None and 0 <= idx < len(self._inventory_costs):
            defaults = self._cost_to_defaults(self._inventory_costs[idx])
        else:
            defaults = {}

        schema = self._build_cost_rule_schema()
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="edit_inventory_cost",
            data_schema=schema,
            errors=errors,
        )

    # --- Schema builders ---

    def _build_schema(
        self,
        participants: list[str],
        input_fields: InputFieldGroups,
        section_inclusion_map: dict[str, dict[str, list[str]]],
        current_connection: str | None = None,
        subentry_data: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Build the schema with name, connection, and choose selectors for main inputs."""
        field_schema = get_input_field_schema_info(ELEMENT_TYPE, input_fields)
        return build_sectioned_choose_schema(
            self._get_sections(),
            input_fields,
            field_schema,
            section_inclusion_map,
            current_data=subentry_data,
            top_level_entries=build_common_fields(
                include_connection=True,
                participants=participants,
                current_connection=current_connection,
            ),
        )

    def _build_cost_rule_schema(self) -> vol.Schema:
        """Build the schema for adding or editing an inventory cost rule."""
        direction_options: list[SelectOptionDict] = [
            SelectOptionDict(value=DIRECTION_ABOVE, label="Above"),
            SelectOptionDict(value=DIRECTION_BELOW, label="Below"),
        ]
        return vol.Schema(
            {
                vol.Required(CONF_COST_NAME): str,
                vol.Required(CONF_DIRECTION): SelectSelector(
                    SelectSelectorConfig(
                        options=direction_options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_THRESHOLD): NumberSelector(
                    NumberSelectorConfig(min=0, step=0.1, mode=NumberSelectorMode.BOX, unit_of_measurement="kWh")
                ),
                vol.Required(CONF_COST): NumberSelector(
                    NumberSelectorConfig(min=0, step=0.01, mode=NumberSelectorMode.BOX, unit_of_measurement="$/kWh")
                ),
            }
        )

    def _build_manage_costs_schema(self) -> vol.Schema:
        """Build the schema for the inventory cost management menu."""
        rule_options: list[SelectOptionDict] = [
            SelectOptionDict(
                value=str(i),
                label=f"{rule[CONF_COST_NAME]} ({rule[CONF_DIRECTION]} {rule[CONF_THRESHOLD].get('value', '?')} kWh)",
            )
            if isinstance(rule[CONF_THRESHOLD], dict)
            else SelectOptionDict(value=str(i), label=rule[CONF_COST_NAME])
            for i, rule in enumerate(self._inventory_costs)
        ]
        action_options: list[SelectOptionDict] = [
            SelectOptionDict(value=ACTION_EDIT, label="Edit"),
            SelectOptionDict(value=ACTION_DELETE, label="Delete"),
        ]
        return vol.Schema(
            {
                vol.Required(CONF_COST_RULE): SelectSelector(
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

    # --- Defaults builders ---

    def _build_defaults(
        self,
        default_name: str,
        input_fields: InputFieldGroups,
        subentry_data: dict[str, Any] | None = None,
        connection_default: str | None = None,
    ) -> dict[str, Any]:
        """Build default values for the main form."""
        connection_default = (
            connection_default
            if connection_default is not None
            else get_connection_target_name(subentry_data.get(CONF_CONNECTION))
            if subentry_data
            else None
        )
        section_defaults = build_sectioned_choose_defaults(
            self._get_sections(),
            input_fields,
            current_data=subentry_data,
        )
        return {
            CONF_NAME: default_name if subentry_data is None else subentry_data.get(CONF_NAME),
            CONF_CONNECTION: connection_default,
            **section_defaults,
        }

    # --- Validation ---

    def _validate_user_input(
        self,
        user_input: dict[str, Any] | None,
        input_fields: InputFieldGroups,
    ) -> dict[str, str] | None:
        """Validate user input and return errors dict if any."""
        if user_input is None:
            return None
        errors: dict[str, str] = {}
        self._validate_name(user_input.get(CONF_NAME), errors)
        field_schema = get_input_field_schema_info(ELEMENT_TYPE, input_fields)
        errors.update(
            validate_sectioned_choose_fields(
                user_input,
                input_fields,
                field_schema,
                self._get_sections(),
            )
        )
        return errors if errors else None

    def _validate_cost_rule(
        self,
        user_input: dict[str, Any],
        errors: dict[str, str],
        *,
        exclude_index: int | None = None,
    ) -> bool:
        """Validate an inventory cost rule. Returns True if valid."""
        name = user_input.get(CONF_COST_NAME)
        if not name:
            errors[CONF_COST_NAME] = "missing_name"
            return False

        existing_names = {
            rule[CONF_COST_NAME] for i, rule in enumerate(self._inventory_costs) if i != exclude_index
        }
        if name in existing_names:
            errors[CONF_COST_NAME] = "name_exists"
            return False

        return True

    # --- Input parsing ---

    def _parse_cost_input(self, user_input: dict[str, Any]) -> InventoryCostConfig:
        """Convert form input into an InventoryCostConfig."""
        threshold = user_input[CONF_THRESHOLD]
        threshold_value = (
            as_entity_value(threshold) if isinstance(threshold, list) else as_constant_value(float(threshold))
        )

        cost_val = user_input[CONF_COST]
        cost_value = as_entity_value(cost_val) if isinstance(cost_val, list) else as_constant_value(float(cost_val))

        return InventoryCostConfig(
            name=user_input[CONF_COST_NAME],
            direction=user_input[CONF_DIRECTION],
            threshold=threshold_value,
            cost=cost_value,
        )

    def _cost_to_defaults(self, rule: InventoryCostConfig) -> dict[str, Any]:
        """Convert a stored cost rule back to form defaults."""
        defaults: dict[str, Any] = {
            CONF_COST_NAME: rule[CONF_COST_NAME],
            CONF_DIRECTION: rule[CONF_DIRECTION],
        }
        threshold = rule[CONF_THRESHOLD]
        if is_constant_value(threshold) or is_entity_value(threshold):
            defaults[CONF_THRESHOLD] = threshold["value"]
        cost_val = rule[CONF_COST]
        if is_constant_value(cost_val) or is_entity_value(cost_val):
            defaults[CONF_COST] = cost_val["value"]
        return defaults

    def _cost_to_edit_input(self, rule: InventoryCostConfig) -> dict[str, Any]:
        """Convert a stored cost rule into parse-ready form input values."""
        input_values: dict[str, Any] = {
            CONF_COST_NAME: rule[CONF_COST_NAME],
            CONF_DIRECTION: rule[CONF_DIRECTION],
        }
        threshold = rule[CONF_THRESHOLD]
        if is_constant_value(threshold) or is_entity_value(threshold):
            input_values[CONF_THRESHOLD] = threshold["value"]
        cost_val = rule[CONF_COST]
        if is_constant_value(cost_val) or is_entity_value(cost_val):
            input_values[CONF_COST] = cost_val["value"]
        return input_values

    # --- Config building ---

    def _build_config(self, main_input: dict[str, Any]) -> dict[str, Any]:
        """Build final config dict from user input."""
        input_fields = get_input_fields(ELEMENT_TYPE)
        sections = self._get_sections()
        config_dict = convert_sectioned_choose_data_to_config(
            main_input,
            input_fields,
            sections,
        )

        result = {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE,
            CONF_NAME: main_input[CONF_NAME],
            CONF_CONNECTION: normalize_connection_target(main_input[CONF_CONNECTION]),
            **config_dict,
        }
        if self._inventory_costs:
            result[CONF_INVENTORY_COSTS] = list(self._inventory_costs)
        return result

    def _update_inventory_costs(self, subentry_data: dict[str, Any]) -> SubentryFlowResult:
        """Update the subentry with modified inventory costs."""
        updated_data = {**subentry_data}
        if self._inventory_costs:
            updated_data[CONF_INVENTORY_COSTS] = list(self._inventory_costs)
        elif CONF_INVENTORY_COSTS in updated_data:
            del updated_data[CONF_INVENTORY_COSTS]

        subentry = self._get_subentry()
        return self.async_update_and_abort(
            self._get_entry(),
            subentry,
            title=subentry.title,
            data=updated_data,
        )

    def _finalize(self, config: dict[str, Any]) -> SubentryFlowResult:
        """Finalize the flow by creating or updating the entry."""
        name = str(self._step1_data[CONF_NAME])
        subentry = self._get_subentry()
        if subentry is not None:
            return self.async_update_and_abort(self._get_entry(), subentry, title=name, data=config)
        return self.async_create_entry(title=name, data=config)
