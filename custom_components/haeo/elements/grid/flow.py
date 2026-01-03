"""Grid element configuration flows."""

from typing import Any, ClassVar, cast

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.flows.constants import ensure_configurable_entities_exist
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_exclusion_map, build_participant_selector
from custom_components.haeo.flows.field_schema import (
    build_constant_value_schema,
    build_entity_schema_entry,
    can_reuse_constant_values,
    convert_entity_selections_to_config,
    extract_entity_selections,
    get_constant_value_defaults,
    get_entity_selection_defaults,
    has_constant_selection,
)

from .schema import CONF_CONNECTION, ELEMENT_TYPE, INPUT_FIELDS, GridConfigSchema


def _build_step1_schema(
    hass: HomeAssistant,
    participants: list[str],
    exclusion_map: dict[str, list[str]],
    current_connection: str | None = None,
) -> vol.Schema:
    """Build the schema for step 1: name, connection, and entity selections."""
    schema_dict: dict[vol.Marker, Any] = {
        # Name field
        vol.Required(CONF_NAME): vol.All(
            vol.Coerce(str),
            vol.Strip,
            vol.Length(min=1, msg="Name cannot be empty"),
            TextSelector(TextSelectorConfig()),
        ),
        # Connection field
        vol.Required(CONF_CONNECTION): build_participant_selector(participants, current_connection),
    }

    # Add entity selectors for all input fields
    for field_info in INPUT_FIELDS:
        exclude_entities = exclusion_map.get(field_info.field_name, [])
        marker, selector = build_entity_schema_entry(
            hass,
            field_info,
            config_schema=GridConfigSchema,
            exclude_entities=exclude_entities,
        )
        schema_dict[marker] = selector

    return vol.Schema(schema_dict)


class GridSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle grid element configuration flows."""

    has_value_source_step: ClassVar[bool] = True

    def __init__(self) -> None:
        """Initialize the flow handler."""
        super().__init__()
        # Store step 1 data for use in step 2
        self._step1_data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle step 1: name, connection, and entity selection."""
        # Clear step 1 data at start to avoid stale state from incomplete flows
        if user_input is None:
            self._step1_data = {}

        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if self._validate_name(name, errors):
                # Validate entity selections
                for field_info in INPUT_FIELDS:
                    field_name = field_info.field_name
                    entities = user_input.get(field_name, [])
                    is_optional = field_name in GridConfigSchema.__optional_keys__

                    # Required fields must have at least one selection
                    if not is_optional and not entities:
                        errors[field_name] = "required"
                        continue

                if not errors:
                    # Store step 1 data and proceed to step 2
                    self._step1_data = user_input
                    return await self.async_step_values()

        # Ensure constant entities exist before building schema
        ensure_configurable_entities_exist(self.hass)

        # Get default name from translations
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "config_subentries", integrations=[DOMAIN]
        )
        default_name = translations.get(f"component.{DOMAIN}.config_subentries.{ELEMENT_TYPE}.flow_title", "Grid")

        entity_metadata = extract_entity_metadata(self.hass)
        exclusion_map = build_exclusion_map(INPUT_FIELDS, entity_metadata)
        participants = self._get_participant_names()
        schema = _build_step1_schema(self.hass, participants, exclusion_map)

        # Apply default entity selections
        defaults: dict[str, Any] = dict(get_entity_selection_defaults(self.hass, INPUT_FIELDS, GridConfigSchema))
        defaults[CONF_NAME] = default_name
        defaults[CONF_CONNECTION] = None
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_values(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle step 2: constant value entry for fields with HAEO Configurable."""
        errors: dict[str, str] = {}
        exclude_keys = (CONF_NAME, CONF_CONNECTION)

        if user_input is not None:
            name = self._step1_data.get(CONF_NAME)
            connection = self._step1_data.get(CONF_CONNECTION)
            entity_selections = extract_entity_selections(self._step1_data, exclude_keys)
            config_dict = convert_entity_selections_to_config(self.hass, entity_selections, user_input, INPUT_FIELDS)

            # Validate that constant values were provided where needed
            for field_info in INPUT_FIELDS:
                field_name = field_info.field_name
                is_constant = has_constant_selection(self.hass, entity_selections.get(field_name, []))
                is_missing = field_name not in user_input
                is_required = field_name not in GridConfigSchema.__optional_keys__ or field_info.default is None
                if is_constant and is_missing and is_required:
                    errors[field_name] = "required"

            if not errors:
                config: dict[str, Any] = {
                    CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                    CONF_NAME: name,
                    CONF_CONNECTION: connection,
                    **config_dict,
                }
                return self.async_create_entry(title=str(name), data=cast("GridConfigSchema", config))

        entity_selections = extract_entity_selections(self._step1_data, exclude_keys)
        schema = build_constant_value_schema(self.hass, INPUT_FIELDS, entity_selections)

        # Apply default constant values
        defaults = get_constant_value_defaults(self.hass, INPUT_FIELDS, entity_selections)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="values",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step 1: name, connection, and entity selection."""
        # Clear step 1 data at start to avoid stale state from incomplete flows
        if user_input is None:
            self._step1_data = {}

        errors: dict[str, str] = {}
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if self._validate_name(name, errors):
                # Validate entity selections
                for field_info in INPUT_FIELDS:
                    field_name = field_info.field_name
                    entities = user_input.get(field_name, [])
                    is_optional = field_name in GridConfigSchema.__optional_keys__

                    if not is_optional and not entities:
                        errors[field_name] = "required"

                if not errors:
                    # Store step 1 data and proceed to step 2
                    self._step1_data = user_input
                    return await self.async_step_reconfigure_values()

        # Ensure constant entities exist before building schema
        ensure_configurable_entities_exist(self.hass)

        current_connection = subentry.data.get(CONF_CONNECTION)
        entity_metadata = extract_entity_metadata(self.hass)
        exclusion_map = build_exclusion_map(INPUT_FIELDS, entity_metadata)
        participants = self._get_participant_names()
        schema = _build_step1_schema(
            self.hass,
            participants,
            exclusion_map,
            current_connection=current_connection if isinstance(current_connection, str) else None,
        )

        # Apply current values plus inferred entity selections
        current_data = dict(subentry.data)
        entity_defaults = get_entity_selection_defaults(self.hass, INPUT_FIELDS, GridConfigSchema, current_data)
        defaults = {
            CONF_NAME: subentry.data.get(CONF_NAME),
            CONF_CONNECTION: current_connection,
            **entity_defaults,
        }
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
            config_dict = convert_entity_selections_to_config(self.hass, entity_selections, user_input, INPUT_FIELDS)

            # Validate constant values
            for field_info in INPUT_FIELDS:
                field_name = field_info.field_name
                is_constant = has_constant_selection(self.hass, entity_selections.get(field_name, []))
                is_missing = field_name not in user_input
                is_required = field_name not in GridConfigSchema.__optional_keys__ or field_info.default is None
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
                    data=cast("GridConfigSchema", final_config),
                )

        entity_selections = extract_entity_selections(self._step1_data, exclude_keys)
        current_data = dict(subentry.data)

        # Skip step 2 if all constant fields already have stored values
        if can_reuse_constant_values(self.hass, INPUT_FIELDS, entity_selections, current_data):
            name = self._step1_data.get(CONF_NAME)
            connection = self._step1_data.get(CONF_CONNECTION)
            constant_values = get_constant_value_defaults(self.hass, INPUT_FIELDS, entity_selections, current_data)
            config_dict = convert_entity_selections_to_config(
                self.hass, entity_selections, constant_values, INPUT_FIELDS
            )
            skip_config: dict[str, Any] = {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: name,
                CONF_CONNECTION: connection,
                **config_dict,
            }
            return self.async_update_and_abort(
                self._get_entry(),
                subentry,
                title=str(name),
                data=cast("GridConfigSchema", skip_config),
            )

        schema = build_constant_value_schema(self.hass, INPUT_FIELDS, entity_selections, current_data)

        # Get current values for pre-population
        defaults = get_constant_value_defaults(self.hass, INPUT_FIELDS, entity_selections, current_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="reconfigure_values",
            data_schema=schema,
            errors=errors,
        )
