"""Inverter element configuration flows."""

from typing import Any, ClassVar, cast

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.flows.constants import ensure_configurable_entities_exist
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_exclusion_map, build_participant_selector
from custom_components.haeo.flows.field_schema import (
    build_constant_value_schema,
    build_entity_selector_with_constant,
    convert_entity_selections_to_config,
    extract_entity_selections,
    get_constant_value_defaults,
    get_entity_selection_defaults,
    has_constant_selection,
)

from .schema import (
    CONF_CONNECTION,
    CONF_EFFICIENCY_AC_TO_DC,
    CONF_EFFICIENCY_DC_TO_AC,
    CONF_MAX_POWER_AC_TO_DC,
    CONF_MAX_POWER_DC_TO_AC,
    ELEMENT_TYPE,
    INPUT_FIELDS,
    InverterConfigSchema,
)


def _get_field(field_name: str) -> Any:
    """Get field info by name."""
    return next(f for f in INPUT_FIELDS if f.field_name == field_name)


def _build_step1_schema(
    exclusion_map: dict[str, list[str]],
    participants: list[str],
    current_connection: str | None = None,
) -> vol.Schema:
    """Build the schema for step 1: name, connection, and entity selection."""
    return vol.Schema(
        {
            vol.Required(CONF_NAME): vol.All(
                vol.Coerce(str),
                vol.Strip,
                vol.Length(min=1, msg="Name cannot be empty"),
                TextSelector(TextSelectorConfig()),
            ),
            vol.Required(CONF_CONNECTION): build_participant_selector(participants, current_connection),
            vol.Required(CONF_MAX_POWER_DC_TO_AC): build_entity_selector_with_constant(
                _get_field(CONF_MAX_POWER_DC_TO_AC),
                exclude_entities=exclusion_map.get(CONF_MAX_POWER_DC_TO_AC, []),
            ),
            vol.Required(CONF_MAX_POWER_AC_TO_DC): build_entity_selector_with_constant(
                _get_field(CONF_MAX_POWER_AC_TO_DC),
                exclude_entities=exclusion_map.get(CONF_MAX_POWER_AC_TO_DC, []),
            ),
            vol.Optional(CONF_EFFICIENCY_DC_TO_AC, default=[]): build_entity_selector_with_constant(
                _get_field(CONF_EFFICIENCY_DC_TO_AC),
                exclude_entities=exclusion_map.get(CONF_EFFICIENCY_DC_TO_AC, []),
            ),
            vol.Optional(CONF_EFFICIENCY_AC_TO_DC, default=[]): build_entity_selector_with_constant(
                _get_field(CONF_EFFICIENCY_AC_TO_DC),
                exclude_entities=exclusion_map.get(CONF_EFFICIENCY_AC_TO_DC, []),
            ),
        }
    )


class InverterSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle inverter element configuration flows."""

    has_value_source_step: ClassVar[bool] = True

    def __init__(self) -> None:
        """Initialize the flow handler."""
        super().__init__()
        self._step1_data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle step 1: name, connection, and entity selection."""
        if user_input is None:
            self._step1_data = {}

        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if self._validate_name(name, errors):
                # Validate required entity fields
                for field_name in (CONF_MAX_POWER_DC_TO_AC, CONF_MAX_POWER_AC_TO_DC):
                    if not user_input.get(field_name):
                        errors[field_name] = "required"

                if not errors:
                    self._step1_data = user_input
                    return await self.async_step_values()

        # Ensure constant entity exists before building schema
        ensure_configurable_entities_exist()

        # Get default name from translations
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "config_subentries", integrations=[DOMAIN]
        )
        default_name = translations.get(f"component.{DOMAIN}.config_subentries.{ELEMENT_TYPE}.flow_title", "Inverter")

        entity_metadata = extract_entity_metadata(self.hass)
        exclusion_map = build_exclusion_map(INPUT_FIELDS, entity_metadata)
        participants = self._get_participant_names()
        schema = _build_step1_schema(exclusion_map, participants)

        # Apply defaults
        defaults: dict[str, Any] = dict(get_entity_selection_defaults(INPUT_FIELDS, InverterConfigSchema))
        defaults[CONF_NAME] = default_name
        defaults[CONF_CONNECTION] = None
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_values(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle step 2: constant value entry for fields with the configurable entity."""
        errors: dict[str, str] = {}
        exclude_keys = (CONF_NAME, CONF_CONNECTION)

        if user_input is not None:
            name = self._step1_data.get(CONF_NAME)
            connection = self._step1_data.get(CONF_CONNECTION)
            entity_selections = extract_entity_selections(self._step1_data, exclude_keys)
            config_dict = convert_entity_selections_to_config(entity_selections, user_input, INPUT_FIELDS)

            for field_info in INPUT_FIELDS:
                field_name = field_info.field_name
                is_constant = has_constant_selection(entity_selections.get(field_name, []))
                is_missing = field_name not in user_input
                is_required = field_name not in InverterConfigSchema.__optional_keys__
                if is_constant and is_missing and is_required:
                    errors[field_name] = "required"

            if not errors:
                final_config: dict[str, Any] = {
                    CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                    CONF_NAME: name,
                    CONF_CONNECTION: connection,
                    **config_dict,
                }
                return self.async_create_entry(title=name, data=cast("InverterConfigSchema", final_config))

        entity_selections = extract_entity_selections(self._step1_data, exclude_keys)
        schema = build_constant_value_schema(INPUT_FIELDS, entity_selections)

        if not schema.schema:
            name = self._step1_data.get(CONF_NAME)
            connection = self._step1_data.get(CONF_CONNECTION)
            config_dict = convert_entity_selections_to_config(entity_selections, {}, INPUT_FIELDS)
            skip_config: dict[str, Any] = {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: name,
                CONF_CONNECTION: connection,
                **config_dict,
            }
            return self.async_create_entry(title=name, data=cast("InverterConfigSchema", skip_config))

        defaults = get_constant_value_defaults(INPUT_FIELDS, entity_selections)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="values",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step 1: name, connection, and entity selection."""
        if user_input is None:
            self._step1_data = {}

        errors: dict[str, str] = {}
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if self._validate_name(name, errors):
                for field_name in (CONF_MAX_POWER_DC_TO_AC, CONF_MAX_POWER_AC_TO_DC):
                    if not user_input.get(field_name):
                        errors[field_name] = "required"

                if not errors:
                    self._step1_data = user_input
                    return await self.async_step_reconfigure_values()

        ensure_configurable_entities_exist()

        entity_metadata = extract_entity_metadata(self.hass)
        exclusion_map = build_exclusion_map(INPUT_FIELDS, entity_metadata)
        current_connection = subentry.data.get(CONF_CONNECTION)
        participants = self._get_participant_names()
        schema = _build_step1_schema(
            exclusion_map,
            participants,
            current_connection=current_connection if isinstance(current_connection, str) else None,
        )

        current_data = dict(subentry.data)
        defaults: dict[str, Any] = dict(get_entity_selection_defaults(INPUT_FIELDS, InverterConfigSchema, current_data))
        defaults[CONF_NAME] = subentry.data.get(CONF_NAME)
        defaults[CONF_CONNECTION] = current_connection
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure_values(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step 2: constant value entry."""
        errors: dict[str, str] = {}
        subentry = self._get_reconfigure_subentry()
        exclude_keys = (CONF_NAME, CONF_CONNECTION)

        if user_input is not None:
            name = self._step1_data.get(CONF_NAME)
            connection = self._step1_data.get(CONF_CONNECTION)
            entity_selections = extract_entity_selections(self._step1_data, exclude_keys)
            config_dict = convert_entity_selections_to_config(entity_selections, user_input, INPUT_FIELDS)

            for field_info in INPUT_FIELDS:
                field_name = field_info.field_name
                is_constant = has_constant_selection(entity_selections.get(field_name, []))
                is_missing = field_name not in user_input
                is_required = field_name not in InverterConfigSchema.__optional_keys__
                if is_constant and is_missing and is_required:
                    errors[field_name] = "required"

            if not errors:
                final_config: dict[str, Any] = {
                    CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                    CONF_NAME: name,
                    CONF_CONNECTION: connection,
                    **config_dict,
                }
                return self.async_update_and_abort(
                    self._get_entry(),
                    subentry,
                    title=str(name),
                    data=cast("InverterConfigSchema", final_config),
                )

        entity_selections = extract_entity_selections(self._step1_data, exclude_keys)
        current_data = dict(subentry.data)
        schema = build_constant_value_schema(INPUT_FIELDS, entity_selections, current_data)

        # Skip step 2 if no constant fields need input
        if not schema.schema:
            name = self._step1_data.get(CONF_NAME)
            connection = self._step1_data.get(CONF_CONNECTION)
            constant_values = get_constant_value_defaults(INPUT_FIELDS, entity_selections, current_data)
            config_dict = convert_entity_selections_to_config(entity_selections, constant_values, INPUT_FIELDS)
            config: dict[str, Any] = {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: name,
                CONF_CONNECTION: connection,
                **config_dict,
            }
            return self.async_update_and_abort(
                self._get_entry(),
                subentry,
                title=str(name),
                data=cast("InverterConfigSchema", config),
            )

        defaults = get_constant_value_defaults(INPUT_FIELDS, entity_selections, current_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="reconfigure_values",
            data_schema=schema,
            errors=errors,
        )
