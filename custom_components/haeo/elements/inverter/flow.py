"""Inverter element configuration flows."""

from typing import Any, cast

from homeassistant.config_entries import ConfigSubentry, ConfigSubentryFlow, SubentryFlowResult, UnknownSubEntry
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_inclusion_map, build_participant_selector
from custom_components.haeo.flows.field_schema import (
    build_choose_schema_entry,
    convert_choose_data_to_config,
    get_choose_default,
    get_preferred_choice,
)

from .schema import CONF_CONNECTION, ELEMENT_TYPE, INPUT_FIELDS, InverterConfigSchema

# Keys to exclude when converting choose data to config
_EXCLUDE_KEYS = (CONF_NAME, CONF_CONNECTION)


class InverterSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle inverter element configuration flows."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle user step: name, connection, and input configuration."""
        return await self._async_step_user(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step: name, connection, and input configuration."""
        return await self._async_step_user(user_input)

    async def _async_step_user(self, user_input: dict[str, Any] | None) -> SubentryFlowResult:
        """Shared logic for user and reconfigure steps."""
        errors = self._validate_user_input(user_input)
        subentry = self._get_subentry()
        subentry_data = dict(subentry.data) if subentry else None

        if user_input is not None and not errors:
            config = self._build_config(user_input)
            return self._finalize(config, user_input)

        translations = await async_get_translations(
            self.hass, self.hass.config.language, "config_subentries", integrations=[DOMAIN]
        )
        default_name = translations[f"component.{DOMAIN}.config_subentries.{ELEMENT_TYPE}.flow_title"]

        current_connection = subentry_data.get(CONF_CONNECTION) if subentry_data else None
        entity_metadata = extract_entity_metadata(self.hass)
        inclusion_map = build_inclusion_map(INPUT_FIELDS, entity_metadata)
        participants = self._get_participant_names()

        schema = self._build_schema(participants, inclusion_map, current_connection, subentry_data)
        defaults = user_input if user_input is not None else self._build_defaults(default_name, subentry_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    def _build_schema(
        self,
        participants: list[str],
        inclusion_map: dict[str, list[str]],
        current_connection: str | None = None,
        subentry_data: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Build the schema with name, connection, and choose selectors for inputs."""
        schema_dict: dict[vol.Marker, Any] = {
            vol.Required(CONF_NAME): vol.All(
                vol.Coerce(str),
                vol.Strip,
                vol.Length(min=1, msg="Name cannot be empty"),
                TextSelector(TextSelectorConfig()),
            ),
            vol.Required(CONF_CONNECTION): build_participant_selector(participants, current_connection),
        }

        for field_info in INPUT_FIELDS:
            is_optional = field_info.field_name in InverterConfigSchema.__optional_keys__
            include_entities = inclusion_map.get(field_info.field_name)
            preferred = get_preferred_choice(field_info, subentry_data)
            marker, selector = build_choose_schema_entry(
                field_info,
                is_optional=is_optional,
                include_entities=include_entities,
                preferred_choice=preferred,
            )
            schema_dict[marker] = selector

        return vol.Schema(schema_dict)

    def _build_defaults(self, default_name: str, subentry_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build default values for the form."""
        defaults: dict[str, Any] = {
            CONF_NAME: default_name if subentry_data is None else subentry_data.get(CONF_NAME),
            CONF_CONNECTION: subentry_data.get(CONF_CONNECTION) if subentry_data else None,
        }

        entry_id: str | None = None
        subentry_id: str | None = None
        if subentry_data is not None:
            entry = self._get_entry()
            subentry = self._get_subentry()
            entry_id = entry.entry_id
            subentry_id = subentry.subentry_id if subentry else None

        for field_info in INPUT_FIELDS:
            choose_default = get_choose_default(
                field_info,
                current_data=subentry_data,
                entry_id=entry_id,
                subentry_id=subentry_id,
            )
            if choose_default is not None:
                defaults[field_info.field_name] = choose_default

        return defaults

    def _validate_user_input(self, user_input: dict[str, Any] | None) -> dict[str, str] | None:
        """Validate user input and return errors dict if any."""
        if user_input is None:
            return None
        errors: dict[str, str] = {}
        self._validate_name(user_input.get(CONF_NAME), errors)
        self._validate_choose_fields(user_input, errors)
        return errors if errors else None

    def _validate_choose_fields(self, user_input: dict[str, Any], errors: dict[str, str]) -> None:
        """Validate that required choose fields have valid selections."""
        for field_info in INPUT_FIELDS:
            field_name = field_info.field_name
            is_optional = field_name in InverterConfigSchema.__optional_keys__

            if is_optional:
                continue

            value = user_input.get(field_name)
            if not self._is_valid_choose_value(value):
                errors[field_name] = "required"

    def _is_valid_choose_value(self, value: Any) -> bool:
        """Check if a choose selector value is valid (has a selection)."""
        if not isinstance(value, dict):
            return False
        choice = value.get("choice")
        inner_value = value.get("value")
        if choice == "constant":
            return inner_value is not None
        if choice == "entity":
            return bool(inner_value)
        return False

    def _build_config(self, user_input: dict[str, Any]) -> InverterConfigSchema:
        """Build final config dict from user input."""
        name = user_input.get(CONF_NAME)
        connection = user_input.get(CONF_CONNECTION)

        config_dict = convert_choose_data_to_config(user_input, INPUT_FIELDS, _EXCLUDE_KEYS)

        return cast(
            "InverterConfigSchema",
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: name,
                CONF_CONNECTION: connection,
                **config_dict,
            },
        )

    def _finalize(self, config: InverterConfigSchema, user_input: dict[str, Any]) -> SubentryFlowResult:
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
