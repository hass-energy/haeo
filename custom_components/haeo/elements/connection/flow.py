"""Connection element configuration flows."""

from typing import Any, cast

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig, TextSelector, TextSelectorConfig
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_exclusion_map, build_participant_selector

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


def _build_schema(
    exclusion_map: dict[str, list[str]],
    participants: list[str],
    current_source: str | None = None,
    current_target: str | None = None,
) -> vol.Schema:
    """Build the voluptuous schema for connection configuration."""
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
            vol.Optional(CONF_MAX_POWER_SOURCE_TARGET): EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    multiple=True,
                    exclude_entities=exclusion_map.get(CONF_MAX_POWER_SOURCE_TARGET, []),
                )
            ),
            vol.Optional(CONF_MAX_POWER_TARGET_SOURCE): EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    multiple=True,
                    exclude_entities=exclusion_map.get(CONF_MAX_POWER_TARGET_SOURCE, []),
                )
            ),
            vol.Optional(CONF_EFFICIENCY_SOURCE_TARGET): EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    multiple=True,
                    exclude_entities=exclusion_map.get(CONF_EFFICIENCY_SOURCE_TARGET, []),
                )
            ),
            vol.Optional(CONF_EFFICIENCY_TARGET_SOURCE): EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    multiple=True,
                    exclude_entities=exclusion_map.get(CONF_EFFICIENCY_TARGET_SOURCE, []),
                )
            ),
            vol.Optional(CONF_PRICE_SOURCE_TARGET): EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    multiple=True,
                    exclude_entities=exclusion_map.get(CONF_PRICE_SOURCE_TARGET, []),
                )
            ),
            vol.Optional(CONF_PRICE_TARGET_SOURCE): EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    multiple=True,
                    exclude_entities=exclusion_map.get(CONF_PRICE_TARGET_SOURCE, []),
                )
            ),
        }
    )


class ConnectionSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle connection element configuration flows."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle adding a new connection element."""
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
                config = cast("ConnectionConfigSchema", {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **user_input})
                return self.async_create_entry(title=name, data=config)

        entity_metadata = extract_entity_metadata(self.hass)
        exclusion_map = build_exclusion_map(INPUT_FIELDS, entity_metadata)
        participants = self._get_participant_names()
        schema = _build_schema(exclusion_map, participants)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfiguring an existing connection element."""
        errors: dict[str, str] = {}
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if self._validate_name(name, errors):
                # Validate source != target
                source = user_input.get(CONF_SOURCE)
                target = user_input.get(CONF_TARGET)
                if source and target and source == target:
                    errors[CONF_TARGET] = "cannot_connect_to_self"

            if not errors:
                config = cast("ConnectionConfigSchema", {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **user_input})
                return self.async_update_and_abort(
                    self._get_entry(),
                    subentry,
                    title=str(name),
                    data=config,
                )

        entity_metadata = extract_entity_metadata(self.hass)
        exclusion_map = build_exclusion_map(INPUT_FIELDS, entity_metadata)
        current_source = subentry.data.get(CONF_SOURCE)
        current_target = subentry.data.get(CONF_TARGET)
        participants = self._get_participant_names()
        schema = _build_schema(
            exclusion_map,
            participants,
            current_source=current_source if isinstance(current_source, str) else None,
            current_target=current_target if isinstance(current_target, str) else None,
        )
        schema = self.add_suggested_values_to_schema(schema, subentry.data)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )
