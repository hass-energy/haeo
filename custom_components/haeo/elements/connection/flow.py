"""Connection element configuration flows."""

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
    can_reuse_constant_values,
    convert_entity_selections_to_config,
    extract_entity_selections,
    get_constant_value_defaults,
    get_entity_selection_defaults,
)

from .schema import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    CONF_SOURCE,
    CONF_TARGET,
    ELEMENT_TYPE,
    INPUT_FIELDS,
    ConnectionConfigSchema,
)


def _get_field(field_name: str) -> Any:
    """Get field info by name."""
    return next(f for f in INPUT_FIELDS if f.field_name == field_name)


def _build_step1_schema(
    exclusion_map: dict[str, list[str]],
    participants: list[str],
    current_source: str | None = None,
    current_target: str | None = None,
) -> vol.Schema:
    """Build the schema for step 1: name, connections, and entity selection."""
    return vol.Schema(
        {
            vol.Required(CONF_NAME): vol.All(
                vol.Coerce(str),
                vol.Strip,
                vol.Length(min=1, msg="Name cannot be empty"),
                TextSelector(TextSelectorConfig()),
            ),
            vol.Required(CONF_SOURCE): build_participant_selector(participants, current_source),
            vol.Required(CONF_TARGET): build_participant_selector(participants, current_target),
            vol.Optional(CONF_MAX_POWER_SOURCE_TARGET): build_entity_selector_with_constant(
                _get_field(CONF_MAX_POWER_SOURCE_TARGET),
                exclude_entities=exclusion_map.get(CONF_MAX_POWER_SOURCE_TARGET, []),
            ),
            vol.Optional(CONF_MAX_POWER_TARGET_SOURCE): build_entity_selector_with_constant(
                _get_field(CONF_MAX_POWER_TARGET_SOURCE),
                exclude_entities=exclusion_map.get(CONF_MAX_POWER_TARGET_SOURCE, []),
            ),
            vol.Optional(CONF_EFFICIENCY_SOURCE_TARGET): build_entity_selector_with_constant(
                _get_field(CONF_EFFICIENCY_SOURCE_TARGET),
                exclude_entities=exclusion_map.get(CONF_EFFICIENCY_SOURCE_TARGET, []),
            ),
            vol.Optional(CONF_EFFICIENCY_TARGET_SOURCE): build_entity_selector_with_constant(
                _get_field(CONF_EFFICIENCY_TARGET_SOURCE),
                exclude_entities=exclusion_map.get(CONF_EFFICIENCY_TARGET_SOURCE, []),
            ),
            vol.Optional(CONF_PRICE_SOURCE_TARGET): build_entity_selector_with_constant(
                _get_field(CONF_PRICE_SOURCE_TARGET),
                exclude_entities=exclusion_map.get(CONF_PRICE_SOURCE_TARGET, []),
            ),
            vol.Optional(CONF_PRICE_TARGET_SOURCE): build_entity_selector_with_constant(
                _get_field(CONF_PRICE_TARGET_SOURCE),
                exclude_entities=exclusion_map.get(CONF_PRICE_TARGET_SOURCE, []),
            ),
        }
    )


class ConnectionSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle connection element configuration flows."""

    has_value_source_step: ClassVar[bool] = True

    def __init__(self) -> None:
        """Initialize the flow handler."""
        super().__init__()
        self._step1_data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle step 1: name, connections, and entity selection."""
        if user_input is None:
            self._step1_data = {}

        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if self._validate_name(name, errors):
                # Validate source != target
                source = user_input.get(CONF_SOURCE)
                target = user_input.get(CONF_TARGET)
                if source and target and source == target:
                    errors[CONF_TARGET] = "cannot_connect_to_self"

            if not errors:
                self._step1_data = user_input
                return await self.async_step_values()

        # Ensure constant entity exists before building schema
        ensure_configurable_entities_exist()

        # Get default name from translations
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "config_subentries", integrations=[DOMAIN]
        )
        default_name = translations.get(f"component.{DOMAIN}.config_subentries.{ELEMENT_TYPE}.flow_title", "Connection")

        entity_metadata = extract_entity_metadata(self.hass)
        exclusion_map = build_exclusion_map(INPUT_FIELDS, entity_metadata)
        participants = self._get_participant_names()
        schema = _build_step1_schema(exclusion_map, participants)

        # Apply defaults - connection fields are all optional for entity selection
        defaults: dict[str, Any] = dict(get_entity_selection_defaults(INPUT_FIELDS, ConnectionConfigSchema))
        defaults[CONF_NAME] = default_name
        defaults[CONF_SOURCE] = None
        defaults[CONF_TARGET] = None
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_values(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle step 2: constant value entry for fields with the configurable entity."""
        errors: dict[str, str] = {}
        exclude_keys = (CONF_NAME, CONF_SOURCE, CONF_TARGET)

        if user_input is not None:
            name = self._step1_data.get(CONF_NAME)
            source = self._step1_data.get(CONF_SOURCE)
            target = self._step1_data.get(CONF_TARGET)
            entity_selections = extract_entity_selections(self._step1_data, exclude_keys)
            config_dict = convert_entity_selections_to_config(entity_selections, user_input, INPUT_FIELDS)

            # Connection fields are all optional, no required validation needed
            if not errors:
                final_config: dict[str, Any] = {
                    CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                    CONF_NAME: name,
                    CONF_SOURCE: source,
                    CONF_TARGET: target,
                    **config_dict,
                }
                return self.async_create_entry(title=name, data=cast("ConnectionConfigSchema", final_config))

        entity_selections = extract_entity_selections(self._step1_data, exclude_keys)
        schema = build_constant_value_schema(INPUT_FIELDS, entity_selections)

        if not schema.schema:
            name = self._step1_data.get(CONF_NAME)
            source = self._step1_data.get(CONF_SOURCE)
            target = self._step1_data.get(CONF_TARGET)
            config_dict = convert_entity_selections_to_config(entity_selections, {}, INPUT_FIELDS)
            config: dict[str, Any] = {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: name,
                CONF_SOURCE: source,
                CONF_TARGET: target,
                **config_dict,
            }
            return self.async_create_entry(title=name, data=cast("ConnectionConfigSchema", config))

        defaults = get_constant_value_defaults(INPUT_FIELDS, entity_selections)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="values",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step 1: name, connections, and entity selection."""
        if user_input is None:
            self._step1_data = {}

        errors: dict[str, str] = {}
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if self._validate_name(name, errors):
                source = user_input.get(CONF_SOURCE)
                target = user_input.get(CONF_TARGET)
                if source and target and source == target:
                    errors[CONF_TARGET] = "cannot_connect_to_self"

            if not errors:
                self._step1_data = user_input
                return await self.async_step_reconfigure_values()

        ensure_configurable_entities_exist()

        entity_metadata = extract_entity_metadata(self.hass)
        exclusion_map = build_exclusion_map(INPUT_FIELDS, entity_metadata)
        current_source = subentry.data.get(CONF_SOURCE)
        current_target = subentry.data.get(CONF_TARGET)
        participants = self._get_participant_names()
        schema = _build_step1_schema(
            exclusion_map,
            participants,
            current_source=current_source if isinstance(current_source, str) else None,
            current_target=current_target if isinstance(current_target, str) else None,
        )

        current_data = dict(subentry.data)
        entity_defaults = get_entity_selection_defaults(INPUT_FIELDS, ConnectionConfigSchema, current_data)
        defaults: dict[str, Any] = dict(entity_defaults)
        defaults[CONF_NAME] = subentry.data.get(CONF_NAME)
        defaults[CONF_SOURCE] = current_source
        defaults[CONF_TARGET] = current_target
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
        exclude_keys = (CONF_NAME, CONF_SOURCE, CONF_TARGET)

        if user_input is not None:
            name = self._step1_data.get(CONF_NAME)
            source = self._step1_data.get(CONF_SOURCE)
            target = self._step1_data.get(CONF_TARGET)
            entity_selections = extract_entity_selections(self._step1_data, exclude_keys)
            config_dict = convert_entity_selections_to_config(entity_selections, user_input, INPUT_FIELDS)

            if not errors:
                final_config: dict[str, Any] = {
                    CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                    CONF_NAME: name,
                    CONF_SOURCE: source,
                    CONF_TARGET: target,
                    **config_dict,
                }
                return self.async_update_and_abort(
                    self._get_entry(),
                    subentry,
                    title=str(name),
                    data=cast("ConnectionConfigSchema", final_config),
                )

        entity_selections = extract_entity_selections(self._step1_data, exclude_keys)
        current_data = dict(subentry.data)

        # Skip step 2 if no constant fields or all constant fields already have stored values
        if can_reuse_constant_values(INPUT_FIELDS, entity_selections, current_data):
            name = self._step1_data.get(CONF_NAME)
            source = self._step1_data.get(CONF_SOURCE)
            target = self._step1_data.get(CONF_TARGET)
            constant_values = get_constant_value_defaults(INPUT_FIELDS, entity_selections, current_data)
            config_dict = convert_entity_selections_to_config(entity_selections, constant_values, INPUT_FIELDS)
            config: dict[str, Any] = {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: name,
                CONF_SOURCE: source,
                CONF_TARGET: target,
                **config_dict,
            }
            return self.async_update_and_abort(
                self._get_entry(),
                subentry,
                title=str(name),
                data=cast("ConnectionConfigSchema", config),
            )

        schema = build_constant_value_schema(INPUT_FIELDS, entity_selections, current_data)
        defaults = get_constant_value_defaults(INPUT_FIELDS, entity_selections, current_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="reconfigure_values",
            data_schema=schema,
            errors=errors,
        )
