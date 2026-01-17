"""Connection element configuration flows."""

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigSubentry, ConfigSubentryFlow, SubentryFlowResult, UnknownSubEntry
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.elements import is_element_config_schema
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_inclusion_map, build_participant_selector
from custom_components.haeo.flows.field_schema import (
    build_choose_schema_entry,
    convert_choose_data_to_config,
    get_choose_default,
    get_preferred_choice,
    preprocess_choose_selector_input,
    validate_choose_fields,
)

from .adapter import adapter
from .schema import CONF_SOURCE, CONF_TARGET, ELEMENT_TYPE, ConnectionConfigSchema

# Keys to exclude when converting choose data to config
_EXCLUDE_KEYS = (CONF_NAME, CONF_SOURCE, CONF_TARGET)


class ConnectionSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle connection element configuration flows."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle user step: name, source, target, and input configuration."""
        return await self._async_step_user(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step: name, source, target, and input configuration."""
        return await self._async_step_user(user_input)

    async def _async_step_user(self, user_input: dict[str, Any] | None) -> SubentryFlowResult:
        """Shared logic for user and reconfigure steps."""
        subentry = self._get_subentry()
        subentry_data = dict(subentry.data) if subentry else None
        participants = self._get_participant_names()
        current_source = subentry_data.get(CONF_SOURCE) if subentry_data else None
        current_target = subentry_data.get(CONF_TARGET) if subentry_data else None

        if (
            subentry_data is not None
            and is_element_config_schema(subentry_data)
            and subentry_data["element_type"] == ELEMENT_TYPE
        ):
            element_config = subentry_data
        else:
            translations = await async_get_translations(
                self.hass, self.hass.config.language, "config_subentries", integrations=[DOMAIN]
            )
            default_name = translations[f"component.{DOMAIN}.config_subentries.{ELEMENT_TYPE}.flow_title"]
            if not isinstance(current_source, str):
                current_source = participants[0] if participants else ""
            if not isinstance(current_target, str):
                current_target = participants[min(1, len(participants) - 1)] if participants else ""
            element_config: ConnectionConfigSchema = {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: default_name,
                CONF_SOURCE: current_source,
                CONF_TARGET: current_target,
            }

        input_fields = adapter.inputs(element_config)

        user_input = preprocess_choose_selector_input(user_input, input_fields)
        errors = self._validate_user_input(user_input, input_fields)

        if user_input is not None and not errors:
            config = self._build_config(user_input)
            return self._finalize(config, user_input)

        entity_metadata = extract_entity_metadata(self.hass)
        inclusion_map = build_inclusion_map(input_fields, entity_metadata)
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "config_subentries", integrations=[DOMAIN]
        )
        default_name = translations[f"component.{DOMAIN}.config_subentries.{ELEMENT_TYPE}.flow_title"]

        schema = self._build_schema(
            participants,
            input_fields,
            inclusion_map,
            current_source,
            current_target,
            dict(subentry_data) if subentry_data is not None else None,
        )
        defaults = (
            user_input
            if user_input is not None
            else self._build_defaults(
                default_name,
                dict(subentry_data) if subentry_data is not None else None,
            )
        )
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    def _build_schema(
        self,
        participants: list[str],
        input_fields: Mapping[str, InputFieldInfo[Any]],
        inclusion_map: dict[str, list[str]],
        current_source: str | None = None,
        current_target: str | None = None,
        subentry_data: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Build the schema with name, source, target, and choose selectors for inputs."""
        schema_dict: dict[vol.Marker, Any] = {
            vol.Required(CONF_NAME): vol.All(
                vol.Coerce(str),
                vol.Strip,
                vol.Length(min=1, msg="Name cannot be empty"),
                TextSelector(TextSelectorConfig()),
            ),
            vol.Required(CONF_SOURCE): build_participant_selector(participants, current_source),
            vol.Required(CONF_TARGET): build_participant_selector(participants, current_target),
        }

        for field_info in input_fields.values():
            is_optional = (
                field_info.field_name in ConnectionConfigSchema.__optional_keys__ and not field_info.force_required
            )
            include_entities = inclusion_map.get(field_info.field_name)
            preferred = get_preferred_choice(field_info, subentry_data, is_optional=is_optional)
            marker, selector = build_choose_schema_entry(
                field_info,
                is_optional=is_optional,
                include_entities=include_entities,
                preferred_choice=preferred,
            )
            schema_dict[marker] = selector

        return vol.Schema(schema_dict)

    def _build_defaults(
        self,
        default_name: str,
        subentry_data: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build default values for the form."""
        defaults: dict[str, Any] = {
            CONF_NAME: default_name if subentry_data is None else subentry_data.get(CONF_NAME),
            CONF_SOURCE: subentry_data.get(CONF_SOURCE) if subentry_data else None,
            CONF_TARGET: subentry_data.get(CONF_TARGET) if subentry_data else None,
        }

        input_fields = adapter.inputs(subentry_data)
        for field_info in input_fields.values():
            choose_default = get_choose_default(field_info, subentry_data)
            if choose_default is not None:
                defaults[field_info.field_name] = choose_default

        return defaults

    def _validate_user_input(
        self,
        user_input: dict[str, Any] | None,
        input_fields: Mapping[str, InputFieldInfo[Any]],
    ) -> dict[str, str] | None:
        """Validate user input and return errors dict if any."""
        if user_input is None:
            return None
        errors: dict[str, str] = {}
        self._validate_name(user_input.get(CONF_NAME), errors)
        errors.update(validate_choose_fields(user_input, input_fields, ConnectionConfigSchema.__optional_keys__))
        # Validate source != target
        source = user_input.get(CONF_SOURCE)
        target = user_input.get(CONF_TARGET)
        if source and target and source == target:
            errors[CONF_TARGET] = "cannot_connect_to_self"
        return errors if errors else None

    def _build_config(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Build final config dict from user input."""
        name = user_input.get(CONF_NAME)
        source = user_input.get(CONF_SOURCE)
        target = user_input.get(CONF_TARGET)
        seed_config = {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE,
            CONF_NAME: name,
            CONF_SOURCE: source,
            CONF_TARGET: target,
        }
        input_fields = adapter.inputs(seed_config)
        config_dict = convert_choose_data_to_config(user_input, input_fields, _EXCLUDE_KEYS)

        return {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE,
            CONF_NAME: name,
            CONF_SOURCE: source,
            CONF_TARGET: target,
            **config_dict,
        }

    def _finalize(self, config: dict[str, Any], user_input: dict[str, Any]) -> SubentryFlowResult:
        """Finalize the flow by creating or updating the entry."""
        name = str(user_input.get(CONF_NAME))
        subentry = self._get_subentry()
        if subentry is not None:
            return self.async_update_and_abort(self._get_entry(), subentry, title=name, data=config)
        return self.async_create_entry(title=name, data=config)

    def _get_subentry(self) -> ConfigSubentry | None:
        """Get the subentry being reconfigured, or None for new entries."""
        try:
            return self._get_reconfigure_subentry()
        except (ValueError, UnknownSubEntry):
            return None
