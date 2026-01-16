"""Battery section element configuration flows."""

from typing import Any, cast

from homeassistant.config_entries import ConfigSubentry, ConfigSubentryFlow, SubentryFlowResult, UnknownSubEntry
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_inclusion_map
from custom_components.haeo.flows.field_schema import (
    build_choose_schema_entry,
    convert_choose_data_to_config,
    get_choose_default,
    get_preferred_choice,
    preprocess_choose_selector_input,
    validate_choose_fields,
)

from .schema import ELEMENT_TYPE, INPUT_FIELDS, BatterySectionConfigSchema

# Keys to exclude when converting choose data to config
_EXCLUDE_KEYS = (CONF_NAME,)


class BatterySectionSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle battery section element configuration flows."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle user step: name and input configuration."""
        return await self._async_step_user(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step: name and input configuration."""
        return await self._async_step_user(user_input)

    async def _async_step_user(self, user_input: dict[str, Any] | None) -> SubentryFlowResult:
        """Shared logic for user and reconfigure steps."""
        user_input = preprocess_choose_selector_input(user_input, INPUT_FIELDS)
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

        entity_metadata = extract_entity_metadata(self.hass)
        inclusion_map = build_inclusion_map(INPUT_FIELDS, entity_metadata)

        schema = self._build_schema(inclusion_map, subentry_data)
        defaults = user_input if user_input is not None else self._build_defaults(default_name, subentry_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    def _build_schema(
        self,
        inclusion_map: dict[str, list[str]],
        subentry_data: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Build the schema with name and choose selectors for inputs."""
        schema_dict: dict[vol.Marker, Any] = {
            vol.Required(CONF_NAME): vol.All(
                vol.Coerce(str),
                vol.Strip,
                vol.Length(min=1, msg="Name cannot be empty"),
                TextSelector(TextSelectorConfig()),
            ),
        }

        for field_info in INPUT_FIELDS:
            is_optional = (
                field_info.field_name in BatterySectionConfigSchema.__optional_keys__ and not field_info.force_required
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

    def _build_defaults(self, default_name: str, subentry_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build default values for the form."""
        defaults: dict[str, Any] = {
            CONF_NAME: default_name if subentry_data is None else subentry_data.get(CONF_NAME),
        }

        for field_info in INPUT_FIELDS:
            choose_default = get_choose_default(field_info, subentry_data)
            if choose_default is not None:
                defaults[field_info.field_name] = choose_default

        return defaults

    def _validate_user_input(self, user_input: dict[str, Any] | None) -> dict[str, str] | None:
        """Validate user input and return errors dict if any."""
        if user_input is None:
            return None
        errors: dict[str, str] = {}
        self._validate_name(user_input.get(CONF_NAME), errors)
        errors.update(validate_choose_fields(user_input, INPUT_FIELDS, BatterySectionConfigSchema.__optional_keys__))
        return errors if errors else None

    def _build_config(self, user_input: dict[str, Any]) -> BatterySectionConfigSchema:
        """Build final config dict from user input."""
        name = user_input.get(CONF_NAME)

        config_dict = convert_choose_data_to_config(user_input, INPUT_FIELDS, _EXCLUDE_KEYS)

        return cast(
            "BatterySectionConfigSchema",
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: name,
                **config_dict,
            },
        )

    def _finalize(self, config: BatterySectionConfigSchema, user_input: dict[str, Any]) -> SubentryFlowResult:
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
