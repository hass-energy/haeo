"""Inverter element configuration flows."""

from typing import Any, cast

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
)
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_exclusion_map, build_participant_selector

from .schema import (
    CONF_CONNECTION,
    CONF_EFFICIENCY_AC_TO_DC,
    CONF_EFFICIENCY_DC_TO_AC,
    CONF_MAX_POWER_AC_TO_DC,
    CONF_MAX_POWER_DC_TO_AC,
    DEFAULTS,
    ELEMENT_TYPE,
    INPUT_FIELDS,
    InverterConfigSchema,
)


def _build_schema(
    exclusion_map: dict[str, list[str]],
    participants: list[str],
    current_connection: str | None = None,
) -> vol.Schema:
    """Build the voluptuous schema for inverter configuration."""
    return vol.Schema(
        {
            vol.Required(CONF_NAME): vol.All(
                vol.Coerce(str),
                vol.Strip,
                vol.Length(min=1, msg="Name cannot be empty"),
                TextSelector(TextSelectorConfig()),
            ),
            vol.Required(CONF_CONNECTION): build_participant_selector(participants, current_connection),
            vol.Required(CONF_MAX_POWER_DC_TO_AC): EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    multiple=True,
                    exclude_entities=exclusion_map.get(CONF_MAX_POWER_DC_TO_AC, []),
                )
            ),
            vol.Required(CONF_MAX_POWER_AC_TO_DC): EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    multiple=True,
                    exclude_entities=exclusion_map.get(CONF_MAX_POWER_AC_TO_DC, []),
                )
            ),
            vol.Optional(CONF_EFFICIENCY_DC_TO_AC): vol.All(
                vol.Coerce(float),
                vol.Range(min=0, max=100, msg="Value must be between 0 and 100"),
                NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX,
                        min=0,
                        max=100,
                        step="any",
                        unit_of_measurement=PERCENTAGE,
                    )
                ),
            ),
            vol.Optional(CONF_EFFICIENCY_AC_TO_DC): vol.All(
                vol.Coerce(float),
                vol.Range(min=0, max=100, msg="Value must be between 0 and 100"),
                NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX,
                        min=0,
                        max=100,
                        step="any",
                        unit_of_measurement=PERCENTAGE,
                    )
                ),
            ),
        }
    )


class InverterSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle inverter element configuration flows."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle adding a new inverter element."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if self._validate_name(name, errors):
                config = cast("InverterConfigSchema", {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **user_input})
                return self.async_create_entry(title=name, data=config)

        # Get default name from translations
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "config_subentries", integrations=[DOMAIN]
        )
        default_name = translations.get(f"component.{DOMAIN}.config_subentries.{ELEMENT_TYPE}.flow_title", "Inverter")

        entity_metadata = extract_entity_metadata(self.hass)
        exclusion_map = build_exclusion_map(INPUT_FIELDS, entity_metadata)
        participants = self._get_participant_names()
        schema = _build_schema(exclusion_map, participants)
        schema = self.add_suggested_values_to_schema(schema, {CONF_NAME: default_name, **DEFAULTS})

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfiguring an existing inverter element."""
        errors: dict[str, str] = {}
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if self._validate_name(name, errors):
                config = cast("InverterConfigSchema", {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **user_input})
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
        )
