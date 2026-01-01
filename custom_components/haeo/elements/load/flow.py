"""Load element configuration flows."""

from typing import Any, cast

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig, TextSelector, TextSelectorConfig
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN, URL_HAFO
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_exclusion_map, build_participant_selector

from .schema import CONF_CONNECTION, CONF_FORECAST, ELEMENT_TYPE, INPUT_FIELDS, LoadConfigSchema


def _build_schema(
    exclusion_map: dict[str, list[str]],
    participants: list[str],
    current_connection: str | None = None,
) -> vol.Schema:
    """Build the voluptuous schema for load configuration."""
    return vol.Schema(
        {
            vol.Required(CONF_NAME): vol.All(
                vol.Coerce(str),
                vol.Strip,
                vol.Length(min=1, msg="Name cannot be empty"),
                TextSelector(TextSelectorConfig()),
            ),
            vol.Required(CONF_CONNECTION): build_participant_selector(participants, current_connection),
            vol.Required(CONF_FORECAST): EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    multiple=True,
                    exclude_entities=exclusion_map.get(CONF_FORECAST, []),
                )
            ),
        }
    )


class LoadSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle load element configuration flows."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle adding a new load element."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if self._validate_name(name, errors):
                config = cast("LoadConfigSchema", {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **user_input})
                return self.async_create_entry(title=name, data=config)

        # Get default name from translations
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "config_subentries", integrations=[DOMAIN]
        )
        default_name = translations.get(f"component.{DOMAIN}.config_subentries.{ELEMENT_TYPE}.flow_title", "Load")

        entity_metadata = extract_entity_metadata(self.hass)
        exclusion_map = build_exclusion_map(INPUT_FIELDS, entity_metadata)
        participants = self._get_participant_names()
        schema = _build_schema(exclusion_map, participants)
        schema = self.add_suggested_values_to_schema(schema, {CONF_NAME: default_name})

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={"hafo_url": URL_HAFO},
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfiguring an existing load element."""
        errors: dict[str, str] = {}
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if self._validate_name(name, errors):
                config = cast("LoadConfigSchema", {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **user_input})
                return self.async_update_and_abort(
                    self._get_entry(),
                    subentry,
                    title=str(name),
                    data=config,
                )

        entity_metadata = extract_entity_metadata(self.hass)
        exclusion_map = build_exclusion_map(INPUT_FIELDS, entity_metadata)
        current_connection = subentry.data.get(CONF_CONNECTION)
        participants = self._get_participant_names()
        schema = _build_schema(
            exclusion_map,
            participants,
            current_connection=current_connection if isinstance(current_connection, str) else None,
        )
        schema = self.add_suggested_values_to_schema(schema, subentry.data)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
            description_placeholders={"hafo_url": URL_HAFO},
        )
