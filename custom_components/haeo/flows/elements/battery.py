"""Battery element configuration flows.

Flow design:
- async_step_user: Configures the battery's settings.
- async_step_reconfigure: Menu to edit the settings, add a holding cost, or
  edit or delete one.
- async_step_add_holding_cost: Adds a holding cost.
- async_step_manage_holding_costs: Selects a holding cost to edit or delete.
- async_step_edit_holding_cost: Edits the selected holding cost.
"""

from collections.abc import Mapping
from typing import Any  # noqa: TID251  # HA flow signatures are Any-typed upstream

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
import voluptuous as vol

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import get_connection_target_name, normalize_connection_target
from custom_components.haeo.core.schema.constant_value import ConstantValue, as_constant_value, is_constant_value
from custom_components.haeo.core.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_CHARGE_COST,
    CONF_COST,
    CONF_DIRECTION,
    CONF_DISCHARGE_COST,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_ENABLED,
    CONF_HOLDING_COST_NAME,
    CONF_HOLDING_COSTS,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_SALVAGE_VALUE,
    CONF_THRESHOLD,
    DIRECTION_ABOVE,
    DIRECTION_BELOW,
    ELEMENT_TYPE,
    SECTION_LIMITS,
    SECTION_PRICING,
    SECTION_STORAGE,
    SURFACED_PRICE_HINTS,
    HoldingCostConfig,
)
from custom_components.haeo.core.schema.entity_value import EntityValue, as_entity_value, is_entity_value
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
)
from custom_components.haeo.core.units import currency_symbol
from custom_components.haeo.elements import (
    get_input_field_schema_info,
    get_list_input_fields,
    get_surfaced_input_fields,
)
from custom_components.haeo.elements.input_fields import AnyInputFieldInfo, InputFieldGroups, localize_input_field
from custom_components.haeo.flows.element_flow import (
    ElementFlowMixin,
    build_inclusion_map,
    build_sectioned_inclusion_map,
)
from custom_components.haeo.flows.entity_metadata import extract_entity_metadata
from custom_components.haeo.flows.field_schema import (
    CHOICE_CONSTANT,
    CHOICE_ENTITY,
    NormalizingChooseSelector,
    SectionDefinition,
    as_mapping,
    as_str,
    build_choose_selector,
    build_sectioned_choose_defaults,
    build_sectioned_choose_schema,
    convert_sectioned_choose_data_to_config,
    preprocess_sectioned_choose_input,
    sectioned_view,
    validate_sectioned_choose_fields,
)
from custom_components.haeo.flows.surfaced_policy import (
    build_surfaced_defaults,
    build_surfaced_schema_entries,
    save_surfaced_rules_from_input,
)
from custom_components.haeo.sections import (
    build_common_fields,
    efficiency_section,
    power_limits_section,
    pricing_section,
)

# Surfaced policy field names (not stored in battery config)
SURFACED_POLICY_FIELDS: frozenset[str] = frozenset({CONF_CHARGE_COST, CONF_DISCHARGE_COST})

# Holding cost fields entered as an entity or a constant
HOLDING_COST_VALUE_FIELDS: tuple[str, ...] = (CONF_THRESHOLD, CONF_COST)

STEP_ADD_HOLDING_COST: str = "add_holding_cost"
STEP_MANAGE_HOLDING_COSTS: str = "manage_holding_costs"
STEP_EDIT_HOLDING_COST: str = "edit_holding_cost"

CONF_HOLDING_COST: str = "holding_cost"
CONF_ACTION: str = "action"
ACTION_EDIT: str = "edit"
ACTION_DELETE: str = "delete"


class BatterySubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle battery element configuration flows."""

    def __init__(self) -> None:
        """Initialize the flow handler."""
        super().__init__()
        self._step1_data: dict[str, object] = {}
        self._editing_index: int | None = None

    def _get_sections(self) -> tuple[SectionDefinition, ...]:
        """Return sections for the main configuration step."""
        return (
            SectionDefinition(
                key=SECTION_STORAGE, fields=(CONF_CAPACITY, CONF_INITIAL_CHARGE_PERCENTAGE), collapsed=False
            ),
            SectionDefinition(
                key=SECTION_LIMITS,
                fields=(
                    CONF_MIN_CHARGE_PERCENTAGE,
                    CONF_MAX_CHARGE_PERCENTAGE,
                ),
                collapsed=False,
            ),
            power_limits_section((CONF_MAX_POWER_TARGET_SOURCE, CONF_MAX_POWER_SOURCE_TARGET), collapsed=False),
            pricing_section((CONF_SALVAGE_VALUE, CONF_CHARGE_COST, CONF_DISCHARGE_COST), collapsed=False),
            efficiency_section((CONF_EFFICIENCY_SOURCE_TARGET, CONF_EFFICIENCY_TARGET_SOURCE), collapsed=True),
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle user step: name, connection, and input configuration."""
        subentry = self._get_subentry()
        subentry_data: dict[str, object] | None = dict(subentry.data) if subentry else None
        participants = self._get_participant_names()
        current_connection = (
            get_connection_target_name(subentry_data.get(CONF_CONNECTION))  # type: ignore[arg-type]  # stored subentry data always matches BatteryConfigSchema
            if subentry_data
            else None
        )
        default_name = await self._async_get_default_name(ELEMENT_TYPE)
        if not isinstance(current_connection, str):
            current_connection = participants[0] if participants else ""

        input_fields = self._get_input_fields(ELEMENT_TYPE)

        sections = self._get_sections()
        user_input = preprocess_sectioned_choose_input(user_input, input_fields, sections)
        errors = self._validate_user_input(user_input, input_fields)

        if user_input is not None and not errors:
            self._step1_data = user_input
            return self._finalize(self._build_config(user_input, subentry_data))

        entity_metadata = extract_entity_metadata(self.hass, self._get_entry())
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

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:  # noqa: ARG002 (a menu step receives no input)
        """Show the menu for editing the settings or the holding costs."""
        menu_options = ["user", STEP_ADD_HOLDING_COST]
        if self._holding_costs():
            menu_options.append(STEP_MANAGE_HOLDING_COSTS)
        return self.async_show_menu(step_id="reconfigure", menu_options=menu_options)

    async def async_step_add_holding_cost(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle adding a holding cost."""
        errors: dict[str, str] = {}
        holding_costs = self._holding_costs()

        if user_input is not None and self._validate_holding_cost(user_input, holding_costs, errors):
            return self._save_holding_costs([*holding_costs, self._parse_holding_cost(user_input)])

        schema = self._build_holding_cost_schema()
        schema = self.add_suggested_values_to_schema(
            schema, user_input if user_input is not None else {CONF_ENABLED: True}
        )
        return self.async_show_form(step_id=STEP_ADD_HOLDING_COST, data_schema=schema, errors=errors)

    async def async_step_manage_holding_costs(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle selecting a holding cost to edit or delete."""
        holding_costs = self._holding_costs()

        if user_input is not None:
            index = int(user_input[CONF_HOLDING_COST])
            if user_input[CONF_ACTION] == ACTION_DELETE:
                return self._save_holding_costs([cost for i, cost in enumerate(holding_costs) if i != index])
            self._editing_index = index
            return await self.async_step_edit_holding_cost()

        schema = vol.Schema(
            {
                vol.Required(CONF_HOLDING_COST): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=str(i), label=cost[CONF_HOLDING_COST_NAME])
                            for i, cost in enumerate(holding_costs)
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_ACTION): SelectSelector(
                    SelectSelectorConfig(
                        options=[ACTION_EDIT, ACTION_DELETE],
                        mode=SelectSelectorMode.DROPDOWN,
                        translation_key="holding_cost_action",
                    )
                ),
            }
        )
        return self.async_show_form(step_id=STEP_MANAGE_HOLDING_COSTS, data_schema=schema)

    async def async_step_edit_holding_cost(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle editing the selected holding cost."""
        errors: dict[str, str] = {}
        holding_costs = self._holding_costs()
        index = self._editing_index
        if index is None:
            msg = "No holding cost selected for editing"
            raise RuntimeError(msg)

        if user_input is not None and self._validate_holding_cost(
            user_input, holding_costs, errors, exclude_index=index
        ):
            updated = list(holding_costs)
            updated[index] = self._parse_holding_cost(user_input)
            return self._save_holding_costs(updated)

        schema = self._build_holding_cost_schema()
        defaults = user_input if user_input is not None else _holding_cost_to_defaults(holding_costs[index])
        schema = self.add_suggested_values_to_schema(schema, defaults)
        return self.async_show_form(step_id=STEP_EDIT_HOLDING_COST, data_schema=schema, errors=errors)

    def _holding_costs(self) -> list[HoldingCostConfig]:
        """Return the holding costs of the battery being reconfigured."""
        subentry = self._get_subentry()
        if subentry is None:
            return []
        return list(subentry.data.get(CONF_HOLDING_COSTS, []))

    def _save_holding_costs(self, holding_costs: list[HoldingCostConfig]) -> SubentryFlowResult:
        """Store the holding costs on the battery being reconfigured."""
        subentry = self._get_reconfigure_subentry()
        data = {key: value for key, value in subentry.data.items() if key != CONF_HOLDING_COSTS}
        if holding_costs:
            data[CONF_HOLDING_COSTS] = holding_costs
        return self.async_update_and_abort(self._get_entry(), subentry, data=data)

    def _holding_cost_field_infos(self) -> dict[str, AnyInputFieldInfo]:
        """Return the input field info for each holding cost field, from the schema's list field hints."""
        list_fields = get_list_input_fields({CONF_ELEMENT_TYPE: ELEMENT_TYPE, CONF_HOLDING_COSTS: [{}]})
        symbol = currency_symbol(self.hass.config.currency)
        return {
            name: localize_input_field(info, symbol) for name, info in list_fields[f"{CONF_HOLDING_COSTS}.0"].items()
        }

    def _build_value_selector(
        self, field_info: AnyInputFieldInfo, include_entities: list[str] | None
    ) -> NormalizingChooseSelector:
        """Build a ChooseSelector for a holding cost field (entity/constant)."""
        return build_choose_selector(
            field_info,
            allowed_choices={CHOICE_ENTITY, CHOICE_CONSTANT},
            include_entities=include_entities,
            multiple=True,
            preferred_choice=CHOICE_CONSTANT,
        )

    def _build_holding_cost_schema(self) -> vol.Schema:
        """Build the schema for adding or editing a holding cost."""
        field_infos = self._holding_cost_field_infos()
        value_field_infos = {name: field_infos[name] for name in HOLDING_COST_VALUE_FIELDS}
        entity_metadata = extract_entity_metadata(self.hass, self._get_entry())
        inclusion_map = build_inclusion_map(value_field_infos, entity_metadata)
        return vol.Schema(
            {
                vol.Required(CONF_HOLDING_COST_NAME): str,
                vol.Required(CONF_ENABLED, default=True): BooleanSelector(BooleanSelectorConfig()),
                vol.Required(CONF_DIRECTION, default=DIRECTION_BELOW): SelectSelector(
                    SelectSelectorConfig(
                        options=[DIRECTION_BELOW, DIRECTION_ABOVE],
                        mode=SelectSelectorMode.LIST,
                        translation_key="holding_cost_direction",
                    )
                ),
                **{
                    vol.Required(name): self._build_value_selector(info, inclusion_map.get(name))
                    for name, info in value_field_infos.items()
                },
            }
        )

    def _validate_holding_cost(
        self,
        user_input: Mapping[str, object],
        holding_costs: list[HoldingCostConfig],
        errors: dict[str, str],
        *,
        exclude_index: int | None = None,
    ) -> bool:
        """Validate a holding cost's fields. Returns True if valid."""
        name = user_input.get(CONF_HOLDING_COST_NAME)
        if not name:
            errors[CONF_HOLDING_COST_NAME] = "missing_name"
        elif any(cost[CONF_HOLDING_COST_NAME] == name for i, cost in enumerate(holding_costs) if i != exclude_index):
            errors[CONF_HOLDING_COST_NAME] = "holding_cost_name_exists"
        for field in HOLDING_COST_VALUE_FIELDS:
            if user_input.get(field) in (None, "", []):
                errors[field] = "required"
        return not errors

    def _parse_holding_cost(self, user_input: Mapping[str, object]) -> HoldingCostConfig:
        """Convert form input into a stored holding cost."""
        return {
            "name": str(user_input[CONF_HOLDING_COST_NAME]),
            "enabled": bool(user_input[CONF_ENABLED]),
            "direction": DIRECTION_ABOVE if user_input[CONF_DIRECTION] == DIRECTION_ABOVE else DIRECTION_BELOW,
            "threshold": _parse_value(user_input[CONF_THRESHOLD]),
            "cost": _parse_value(user_input[CONF_COST]),
        }

    def _build_schema(
        self,
        participants: list[str],
        input_fields: InputFieldGroups,
        section_inclusion_map: dict[str, dict[str, list[str]]],
        current_connection: str | None = None,
        subentry_data: Mapping[str, object] | None = None,
    ) -> vol.Schema:
        """Build the schema with name, connection, and choose selectors for main inputs."""
        field_schema = get_input_field_schema_info(ELEMENT_TYPE, input_fields)
        surfaced_fields = get_surfaced_input_fields(ELEMENT_TYPE)
        element_name = as_str(subentry_data.get(CONF_NAME)) if subentry_data else None
        surfaced_entries = build_surfaced_schema_entries(
            self.hass, self._get_entry(), element_name, SURFACED_PRICE_HINTS, surfaced_fields
        )
        return build_sectioned_choose_schema(
            self._get_sections(),
            input_fields,
            field_schema,
            section_inclusion_map,
            current_data=sectioned_view(subentry_data),
            top_level_entries=build_common_fields(
                include_connection=True,
                participants=participants,
                current_connection=current_connection,
            ),
            extra_field_entries={SECTION_PRICING: surfaced_entries},
        )

    def _build_defaults(
        self,
        default_name: str,
        input_fields: InputFieldGroups,
        subentry_data: Mapping[str, object] | None = None,
        connection_default: str | None = None,
    ) -> dict[str, object]:
        """Build default values for the main form."""
        connection_default = (
            connection_default
            if connection_default is not None
            else get_connection_target_name(subentry_data.get(CONF_CONNECTION))  # type: ignore[arg-type]  # stored subentry data always matches BatteryConfigSchema
            if subentry_data
            else None
        )
        hub_entry = self._get_entry()
        element_name = as_str(subentry_data.get(CONF_NAME)) if subentry_data else None
        surfaced_fields = get_surfaced_input_fields(ELEMENT_TYPE)
        surfaced_defaults = build_surfaced_defaults(hub_entry, element_name, SURFACED_PRICE_HINTS, surfaced_fields)

        section_defaults = build_sectioned_choose_defaults(
            self._get_sections(),
            input_fields,
            current_data=subentry_data,
            base_defaults={SECTION_PRICING: surfaced_defaults},
        )
        return {
            CONF_NAME: default_name if subentry_data is None else subentry_data.get(CONF_NAME),
            CONF_CONNECTION: connection_default,
            **section_defaults,
        }

    def _validate_user_input(
        self,
        user_input: dict[str, object] | None,
        input_fields: InputFieldGroups,
    ) -> dict[str, str] | None:
        """Validate user input and return errors dict if any."""
        if user_input is None:
            return None
        errors: dict[str, str] = {}
        self._validate_name(as_str(user_input.get(CONF_NAME)), errors)
        self._validate_endpoint(as_str(user_input.get(CONF_CONNECTION)), CONF_CONNECTION, errors)
        field_schema = get_input_field_schema_info(ELEMENT_TYPE, input_fields)
        errors.update(
            validate_sectioned_choose_fields(
                user_input,
                input_fields,
                field_schema,
                self._get_sections(),
                exclude_fields=tuple(SURFACED_POLICY_FIELDS),
            )
        )
        return errors if errors else None

    def _build_config(
        self,
        main_input: Mapping[str, object],
        subentry_data: Mapping[str, object] | None,
    ) -> dict[str, object]:
        """Build final config dict from user input, keeping any holding costs already configured."""
        input_fields = self._get_input_fields(ELEMENT_TYPE)
        config_dict = convert_sectioned_choose_data_to_config(
            main_input,
            input_fields,
            self._get_sections(),
            exclude_fields=tuple(SURFACED_POLICY_FIELDS),
        )
        holding_costs = subentry_data.get(CONF_HOLDING_COSTS) if subentry_data else None

        return {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE,
            CONF_NAME: main_input[CONF_NAME],
            CONF_CONNECTION: normalize_connection_target(main_input[CONF_CONNECTION]),  # type: ignore[arg-type]  # user input validated by choose selector against the connection schema
            **config_dict,
            **({CONF_HOLDING_COSTS: holding_costs} if holding_costs else {}),
        }

    def _finalize(self, config: dict[str, object]) -> SubentryFlowResult:
        """Finalize the flow by creating or updating the entry and saving surfaced rules."""
        name = str(self._step1_data[CONF_NAME])

        # Save surfaced policy rules from the pricing section input
        pricing_input = as_mapping(self._step1_data.get(SECTION_PRICING))
        hub_entry = self._get_entry()
        translations = self._surfaced_rule_translations(name)
        subentry = self._get_subentry()
        is_new = subentry is None
        save_surfaced_rules_from_input(
            self.hass,
            hub_entry,
            name,
            pricing_input,
            SURFACED_PRICE_HINTS,
            translations,
            apply_defaults=is_new,
        )

        if subentry is not None:
            return self.async_update_and_abort(self._get_entry(), subentry, title=name, data=config)
        return self.async_create_entry(title=name, data=config)

    def _surfaced_rule_translations(self, element_name: str) -> dict[str, str]:
        """Build translated rule names for surfaced policy rules."""
        return {
            "charge_cost": f"{element_name} charge cost",
            "discharge_cost": f"{element_name} discharge cost",
        }


def _parse_value(value: object) -> EntityValue | ConstantValue:
    """Convert a ChooseSelector value into an entity or constant schema value."""
    if isinstance(value, list):
        return as_entity_value([str(entity_id) for entity_id in value])
    return as_constant_value(float(value))  # type: ignore[arg-type]  # ChooseSelector constant values are numeric


def _holding_cost_to_defaults(holding_cost: HoldingCostConfig) -> dict[str, object]:
    """Convert a stored holding cost back to form defaults."""
    defaults: dict[str, object] = {
        CONF_HOLDING_COST_NAME: holding_cost["name"],
        CONF_ENABLED: holding_cost["enabled"],
        CONF_DIRECTION: holding_cost["direction"],
    }
    for field in HOLDING_COST_VALUE_FIELDS:
        value = holding_cost[field]
        if is_constant_value(value) or is_entity_value(value):
            defaults[field] = value["value"]
    return defaults
